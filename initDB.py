from pymongo import MongoClient

# I created this file thinking to use it incase the db doesn't exist... 
# but I guess mongodb automatically initializes it if not found

client = MongoClient.MongoClient("mongodb://localhost:27017/")
db = client.fileManager

db.create_collection("folders", exist_ok=True)
db.create_collection("files", exist_ok=True)
db.create_collection("textChunks", exist_ok=True)
db.create_collection("tags", exist_ok=True)
db.create_collection("file_tags", exist_ok=True)
db.create_collection("accessLogs", exist_ok=True)
db.create_collection("trashed", exist_ok=True)
