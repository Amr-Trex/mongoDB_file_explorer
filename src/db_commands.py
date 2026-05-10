import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client.fileManager


# -------------------- clear db --------------------
def clear_db(db = db):
    for c in ("files", "folders", "systemFolders", "tags", "file_tags", "textChunks", "accessLog", "trash", "users", "systemArtifacts"):
        db[c].drop()


# -------------------- return count of items in each collection -------------------
def get_counts(db = db):
    return {c: db[c].count_documents({}) for c in ("files", "folders", "systemFolders", "tags", "file_tags", "textChunks", "accessLog", "trash", "users", "systemArtifacts")}


# -------------------- ensure indexes -------------------
# sets up the database for faster searches and automatic cleanup of deleted files by indexing
def ensure_indexes(db = db):
    db.files.create_index([("name", "text")])
    db.folders.create_index([("path", 1)], unique=True)
    db.tags.create_index([("name", 1)], unique=True)
    db.file_tags.create_index([("fileUid", 1), ("tagId", 1)], unique=True)
    db.accessLog.create_index([("timestamp", -1)])
    db.trash.create_index("autoPurgeAt", expireAfterSeconds=0)   # TTL
    db.users.create_index([("username", 1)], unique=True)
    db.systemArtifacts.create_index([("uid", 1)], unique=True)
    db.systemArtifacts.create_index([("name", "text")])
    db.systemFolders.create_index([("path", 1)], unique=True)


# -------------------- pipelines --------------------
# dictionary holding functions that dynamically generate MongoDB aggregation pipelines
AGGREGATION_PIPELINES = {
    # 'search_files' pipeline:
    # 1. $match: Filters documents based on a text search query and any explicit filters (like fileType).
    # 2. $skip: Skips documents for pagination (lazy loading).
    # 3. $limit: Restricts output length for performance.
    "search_files": lambda kwargs: [
        { "$match": { "$text": {"$search": kwargs.get("search_kw", "")}, **kwargs.get("filter_doc", {}) } },
        { "$skip": kwargs.get("offset", 0) },
        { "$limit": kwargs.get("limit", 100) }
    ],
    # 'disk_usage_by_extension' pipeline: Groups files by extension and sums their sizes to analyze storage consumption.
    "disk_usage_by_extension": lambda kwargs: [
        {
            "$group": {
                "_id": "$ext",
                "totalSize": {"$sum": "$size"},
                "count": {"$sum": 1}
            }
        },
        { "$sort": {"totalSize": -1} }
    ],
    # 'find_duplicates' pipeline: Groups files by their SHA256 hash to find items that have multiple identical copies.
    "find_duplicates": lambda kwargs: [
        {
            "$group": {
                "_id": "$hash",
                "count": {"$sum": 1},
                "files": {"$push": "$$ROOT"}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}, 
                "_id": {"$ne": ""}, 
                "_id": {"$ne": None}
            }
        }
    ],
    # 'user_access_metrics' pipeline: Joins accessLog with users to calculate user activity and scan frequencies.
    "user_access_metrics": lambda kwargs: [
        {
            "$lookup": {
                "from": "users",
                "localField": "user",
                "foreignField": "username",
                "as": "userDetails"
            }
        },
        {
            "$group": {
                "_id": "$user",
                "scansCount": {"$sum": 1},
                "domain": {"$first": {"$arrayElemAt": ["$userDetails.domain", 0]}}
            }
        },
        { "$sort": {"scansCount": -1} }
    ]
}


def get_aggregate(name, **kwargs):
    """
    Returns an aggregation pipeline based on its name from the dictionary.
    
    Args:
        name (str): Key matching the pipeline in AGGREGATION_PIPELINES
        **kwargs: Arguments needed to construct the pipeline (search_kw, offset, etc.)
    """
    if name not in AGGREGATION_PIPELINES:
        raise ValueError(f"Aggregation pipeline '{name}' does not exist.")
        
    return AGGREGATION_PIPELINES[name](kwargs)




