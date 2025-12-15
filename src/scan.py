from pymongo import MongoClient
import pathlib, os, datetime, hashlib, mimetypes
from db_commands import get_counts, ensure_indexes

client = MongoClient("mongodb://localhost:27017/")
db = client.fileManager
# ROOT calculation moved to main block

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
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1<<15), b''):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return ""


# -------------------- 6-collection writer --------------------
def scan(root: pathlib.Path, owner="me"):
    ensure_indexes()
    tag_cache = {}        # name -> _id
    for folder, _, files in os.walk(root):
        folder_path = pathlib.Path(folder).resolve()

        # ________________________1.1. folders collection
        fold_doc = {
            "path": str(folder_path), 
            "name": folder_path.name, 
            "owner": owner,
            # date added... for the schema
            "dateAdded": datetime.datetime.now(),
        }
        db.folders.replace_one({"path": fold_doc["path"]}, fold_doc, upsert=True)
        folder_id = db.folders.find_one({"path": str(folder_path)})["_id"]

        for fname in files:
            # the full path of the file
            full = folder_path / fname
            try:
                stat = full.stat()
            except:
                continue
            # finding the user ID for the file
            uid = f"{stat.st_ino}_{int(stat.st_mtime)}"
            # ________________________1.2. files collection ________________________
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

            # _____________________2. textChunks (text files only)
            # TODO: I should edit this so that it includes all text AND code file extensions...
            if file_doc["ext"] in {".txt", ".md", ".py", ".cpp", ".java", ".doc", ".docx"}:
                try:
                    txt = full.read_text(encoding="utf8", errors="ignore")[:4000]
                    db.textChunks.replace_one(
                        {"fileId": uid, "chunkNo": 0},
                        {"fileId": uid, "chunkNo": 0, "text": txt}, upsert=True)

                    # ________________________3. auto-tag by extension  (example)
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

            # ________________________4. accessLog  (fake "scanned" action for demo)
            db.accessLog.insert_one({
                "fileId": uid,
                "user": owner,
                "action": "SCANNED",
                "timestamp": datetime.datetime.now()
            })

    # ________________________5. display final count report
    print("Scan complete.")
    print(get_counts())

if __name__ == "__main__":
    ROOT = pathlib.Path(input("Folder to index: ").strip() or pathlib.Path.home())
    scan(ROOT)