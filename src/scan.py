from pymongo import MongoClient
import pathlib, os, datetime, hashlib, mimetypes

client = MongoClient("mongodb://localhost:27017/")
db = client.fileManager
ROOT = pathlib.Path(input("Folder to index: ").strip() or pathlib.Path.home())

# -------------------- helpers --------------------
def get_hash(path):
    """Calculate the SHA256 hash of a file at the given path.

    This function reads the file in chunks of 32KB and updates
    the hash object with each chunk. The resulting hash
    is returned as a hexadecimal string.

    Args:
        path: The path to the file to hash.

    Returns:
        A hexadecimal string representing the SHA256 hash of
        the file at the given path.
    """
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1<<15), b''):
            h.update(chunk)
    return h.hexdigest()

def ensure_indexes():
    db.files.create_index([("name", "text")])
    db.folders.create_index([("path", 1)], unique=True)
    db.tags.create_index([("name", 1)], unique=True)
    db.file_tags.create_index([("fileUid", 1), ("tagId", 1)], unique=True)
    db.accessLog.create_index([("timestamp", -1)])
    db.trash.create_index("autoPurgeAt", expireAfterSeconds=0)   # TTL

# -------------------- 6-collection writer --------------------
def scan(root: pathlib.Path, owner="me"):
    ensure_indexes()
    tag_cache = {}        # name -> _id
    for folder, _, files in os.walk(root):
        folder_path = pathlib.Path(folder).resolve()

        # 1. folders collection
        fold_doc = {"path": str(folder_path), "name": folder_path.name, "owner": owner}
        db.folders.replace_one({"path": fold_doc["path"]}, fold_doc, upsert=True)
        folder_id = db.folders.find_one({"path": str(folder_path)})["_id"]

        for fname in files:
            full = folder_path / fname
            try:
                stat = full.stat()
            except:
                continue
            uid = f"{stat.st_ino}_{int(stat.st_mtime)}"
            file_doc = {
                "uid": uid,
                "name": fname,
                "ext": full.suffix.lower(),
                "size": stat.st_size,
                "path": str(full),
                "folderId": folder_id,
                "owner": owner,
                "dateAdded": datetime.datetime.now(),
                "dateMod": datetime.datetime.fromtimestamp(stat.st_mtime),
                "hash": get_hash(full),
                "mime": mimetypes.guess_type(str(full))[0] or "unknown"
            }
            db.files.replace_one({"uid": uid}, file_doc, upsert=True)

            # 2. textChunks (text files only)
            # TODO: I should edit this so that it includes all text AND code file extensions...
            if file_doc["ext"] in {".txt", ".md", ".py", ".cpp", ".java", ".doc", ".docx"}:
                try:
                    txt = full.read_text(encoding="utf8", errors="ignore")[:4000]
                    db.textChunks.replace_one(
                        {"fileId": uid, "chunkNo": 0},
                        {"fileId": uid, "chunkNo": 0, "text": txt}, upsert=True)

                    # 3. auto-tag by extension  (example)
                    tag_name = "text-file" if file_doc["ext"] in [".txt", ".md", ".doc", ".docx"] else f"code-file-{file_doc['ext'].lstrip('.')}"
                    if tag_name not in tag_cache:
                        db.tags.replace_one({"name": tag_name}, {"name": tag_name, "owner": owner}, upsert=True)
                        tag_cache[tag_name] = db.tags.find_one({"name": tag_name})["_id"]
                    db.file_tags.replace_one(
                        {"fileUid": uid, "tagId": tag_cache[tag_name]},
                        {"fileUid": uid, "tagId": tag_cache[tag_name]}, upsert=True)
                except:
                    # TODO: also over here... if it's a different file then decide tag_name
                    pass

            # 4. accessLog  (fake "scanned" action for demo)
            db.accessLog.insert_one({
                "fileId": uid,
                "user": owner,
                "action": "SCANNED",
                "timestamp": datetime.datetime.now()
            })

    print("Scan complete.")
    # 5. display stats and final count report
    for c in ("files", "folders", "tags", "file_tags", "textChunks", "accessLog", "trash"):
        print(c + ":", db[c].count_documents({}))

if __name__ == "__main__":
    scan(ROOT)