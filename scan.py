from pymongo import MongoClient
import pathlib, os, datetime, hashlib, mimetypes

client = MongoClient("mongodb://localhost:27017/")
db = client.fileManager

# db.create_collection("folders", exist_ok=True)
# db.create_collection("files", exist_ok=True)
# db.create_collection("textChunks", exist_ok=True)
# db.create_collection("tags", exist_ok=True)
# db.create_collection("file_tags", exist_ok=True)
# db.create_collection("accessLogs", exist_ok=True)
# db.create_collection("trashed", exist_ok=True)

ROOT = pathlib.Path(input("Folder to index: ").strip() or pathlib.Path.home())

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


# ---- indexes (once) ----
db.files.create_index([("name", "text")])
db.folders.create_index([("path", 1)], unique=True)

for folder, _, files in os.walk(ROOT):
    folder_path = pathlib.Path(folder).resolve()
    # 1. folders collection
    fold_doc = {"path": str(folder_path), "name": folder_path.name}
    db.folders.replace_one({"path": fold_doc["path"]}, fold_doc, upsert=True)
    folder_id = db.folders.find_one({"path": str(folder_path)})["_id"]

    for fname in files:
        full = folder_path / fname
        try:
            stat = full.stat()
        except:
            continue
        uid = f"{stat.st_ino}_{int(stat.st_mtime)}"   # simple unique key
        file_doc = {
            "uid": uid,
            "name": fname,
            "ext": full.suffix.lower(),
            "size": stat.st_size,
            "path": str(full),
            "folderId": folder_id,
            "dateAdded": datetime.datetime.utcnow(),
            "hash": get_hash(full),
            "mime": mimetypes.guess_type(str(full))[0] or "unknown"
        }
        db.files.replace_one({"uid": uid}, file_doc, upsert=True)

        # 2. textChunks (only text files)
        if file_doc["ext"] in {".txt", ".md", ".py", ".cpp", ".java"}:
            try:
                txt = full.read_text(encoding="utf8", errors="ignore")[:4000]
                db.textChunks.replace_one(
                    {"fileId": uid, "chunkNo": 0},
                    {"fileId": uid, "chunkNo": 0, "text": txt}, upsert=True)
            except:
                pass

print("Scan complete.")
print("files:", db.files.count_documents({}),
      "folders:", db.folders.count_documents({}),
      "textChunks:", db.textChunks.count_documents({}))