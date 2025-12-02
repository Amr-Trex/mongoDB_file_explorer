MongoDB Project about a file explorer/searcher

(./public/image1.png)

(./public/image2.png)

(./public/image3.png)

(./public/image4.png)

(./public/image5.png)

(./public/image6.png)

(./public/image7.png)

1.  files (one doc ≈ 300 B)

{\
\_id : ObjectId (Mongo gives **this**)\
uid : **string** \# unique key = inode+mtime (or UUID)\
name : **string** \# original name + extension\
ext : **string** \# \".pdf\"\
size : **long** \# bytes\
path : **string** \# full absolute path on disk\
folderId : ObjectId \# pointer to folders collection\
owner : **string** \# \"me\" (multi-user prep)\
dateAdded : ISODate \# when we first saw it\
dateMod : ISODate \# file-system mtime\
hash : **string** \# SHA-256 (dedupe, future integrity check)\
mime : **string** \# \"application/pdf\" (optional)\
meta : sub-document \# ext-specific goodies\
pdf : { pages : **int**, author : **string**, title : **string** }\
apk : { versionName : **string**, minSdk : **int**, iconGridFSId :
ObjectId (thumb) }\
img : { width : **int**, height : **int**, colorSpace : **string** }\
lastOpen : ISODate \# updated by accessLog\
}

2.  folders

{\
\_id : ObjectId\
name : string \# \"Documents\"\
path : string \# \"/home/you/Documents\" (unique)\
parentId: ObjectId\|null \# parent folder \_id (materialised path)\
depth : int \# how deep from root (speed filter)\
owner : string\
}

3.  tags (user-defined labels)

{\
**\_id** : ObjectId\
name: string \# \"uni\", \"tax-2024\", \"holiday\"\
owner: string\
}

4.  file_tags (many-to-many join)

{\
**fileId**: ObjectId \# files.\_id\
tagId : ObjectId \# tags.\_id\
}

5.  textChunks (for full-text search inside files)

{\
fileId : ObjectId\
chunkNo: int \# 0,1,2... (5000 chars each)\
text : string \# actual text slice\
}

6.  accessLog (audit + recent-files + statistics)

{\
fileId : ObjectId\
user : string\
action : string \# OPEN, DOWNLOAD, DELETE, RENAME\
timestamp: ISODate\
ip : string \# optional when we add phone\
}

7.  (optional) trash (soft-delete)

{\
fileId : ObjectId\
deletedAt : ISODate\
autoPurgeAt: ISODate // TTL index = today + 30 days\
}
