import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client.fileManager


# -------------------- clear db --------------------
def clear_db(db = db):
    for c in ("files", "folders", "tags", "file_tags", "textChunks", "accessLog", "trash"):
        db[c].drop()


# -------------------- return count of items in each collection -------------------
def get_counts(db = db):
    return {c: db[c].count_documents({}) for c in ("files", "folders", "tags", "file_tags", "textChunks", "accessLog", "trash")}


# -------------------- ensure indexes -------------------
# sets up the database for faster searches and automatic cleanup of deleted files by indexing
# a feature included in MongoDB
def ensure_indexes(db = db):
    db.files.create_index([("name", "text")])
    db.folders.create_index([("path", 1)], unique=True)
    db.tags.create_index([("name", 1)], unique=True)
    db.file_tags.create_index([("fileUid", 1), ("tagId", 1)], unique=True)
    db.accessLog.create_index([("timestamp", -1)])
    db.trash.create_index("autoPurgeAt", expireAfterSeconds=0)   # TTL



