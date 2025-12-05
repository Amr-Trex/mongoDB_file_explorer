# ms1_test.py

# TESTINGGGGGGGG
from pymongo import MongoClient
# db = MongoClient("mongodb://localhost:27017/").file_manager        # connect to main database
db = MongoClient("mongodb://localhost:27017/").fileManager


# db.files.insert_one({"name": "smoke", "size": 999})        # insert one document
print("inserted count =", len(db.files.find().to_list(length=None)))    