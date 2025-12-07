import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db   = client.fileManager


# -------------------- clear db --------------------
def clear_db():
    for c in ("files", "folders", "tags", "file_tags", "textChunks", "accessLog", "trash"):
        db[c].drop()


# -------------------- return count of items in each collection -------------------
def get_counts():
    return {c: db[c].count_documents({}) for c in ("files", "folders", "tags", "file_tags", "textChunks", "accessLog", "trash")}



