# MongoDB Project about a file explorer/searcher

## Core Collections (10 Total)

### 1. files (Main User Files)

```
{
  _id        : ObjectId
  uid        : string   # inode+mtime
  name       : string   # original name + extension
  ext        : string   # ".pdf"
  size       : long     # bytes
  path       : string   # full absolute path
  folderId   : ObjectId # pointer to folders collection
  owner      : string   # "me"
  userId     : ObjectId # pointer to users collection
  roles      : list     # e.g., ["read", "write"]
  fileType   : string   # "UserFile"
  deviceName : string   # e.g. "Amrtino (Windows11)"
  dateAdded  : ISODate
  dateMod    : ISODate
  hash       : string   # SHA-256 for deduping
  mime       : string
}
```

### 2. folders (Main User Folders)

```
{
  _id        : ObjectId
  name       : string
  path       : string
  owner      : string
  folderType : string   # "userFolder"
  dateAdded  : ISODate
}
```

### 3. systemFolders (OS & Application Caches)

```
{
  _id        : ObjectId
  name       : string
  path       : string
  owner      : string
  folderType : string   # "sysFolder"
  dateAdded  : ISODate
}
```

### 4. systemArtifacts (OS Cache, `.git`, `.thumbnails`)

```
{
  _id        : ObjectId
  uid        : string
  name       : string
  ext        : string
  size       : long
  path       : string
  folderId   : ObjectId
  deviceName : string
  osOrigin   : string   # "Windows", "Git", "MacOS"
  fileType   : string   # "SystemFile"
  dateMod    : ISODate
}
```

### 5. users (RBAC metadata)

```
{
  _id        : ObjectId
  username   : string
  domain     : string
  dateAdded  : ISODate
}
```

### 6. trash (Recycled Items)

```
{
  _id         : ObjectId
  uid         : string
  name        : string
  ext         : string
  size        : long
  path        : string
  folderId    : ObjectId
  deviceName  : string
  fileType    : string   # "TrashFile"
  dateDeleted : ISODate
  autoPurgeAt : ISODate  # TTL index
}
```

### 7. tags (User-defined tags)

```
{
  _id  : ObjectId
  name : string
  owner: string
}
```

### 8. file_tags (Many-to-Many Join Table)

```
{
  _id      : ObjectId
  fileUid  : string
  tagId    : ObjectId
}
```

### 9. textChunks (Extracted Full Text Content)

```
{
  _id      : ObjectId
  fileId   : string
  chunkNo  : int
  text     : string
}
```

### 10. accessLog (Auditing Metrics)

```
{
  _id        : ObjectId
  fileId     : string
  user       : string
  action     : string   # SCANNED, OPEN, etc.
  timestamp  : ISODate
}
```

---

## Aggregation Pipelines Used

MongoDB aggregations dynamically reshape data through pipelines. We abstracted our pipelines natively to improve GUI visualization capabilities:

1. **`search_files`**: Employs `$match` coupled with a text index search (`$text`), merged dynamically against collection Discriminators (e.g., `fileType: UserFile`). It executes `$skip` and `$limit` for active memory pagination logic (Native Lazy Loading).

```json
[
  {
    "$match": { "$text": { "$search": "<search_kw>" }, "fileType": "UserFile" }
  },
  { "$skip": "<offset>" },
  { "$limit": 100 }
]
```

2. **`disk_usage_by_extension`**: Re-maps file storage footprints via `$group` matching on `$ext`. It aggregates (`$sum`) byte sizes together, then processes a descendant `$sort` to dynamically chart file types consuming the most disk space.

```json
[
  {
    "$group": {
      "_id": "$ext",
      "totalSize": { "$sum": "$size" },
      "count": { "$sum": 1 }
    }
  },
  { "$sort": { "totalSize": -1 } }
]
```

3. **`find_duplicates`**: Executes a grouping mechanism spanning `$hash` logic, retaining identical file roots using `$push: $$ROOT`. It relies on an active `$match` to prune results to groupings possessing a `count` > 1 to assist storage cleanup.

```json
[
  {
    "$group": {
      "_id": "$hash",
      "count": { "$sum": 1 },
      "files": { "$push": "$$ROOT" }
    }
  },
  {
    "$match": {
      "count": { "$gt": 1 },
      "_id": { "$ne": "" },
      "_id": { "$ne": null }
    }
  }
]
```

4. **`user_access_metrics`**: A relational data query utilizing `$lookup` executing a Left Outer Join between `accessLog` and `users`. It matches usernames and outputs total system scan statistics per host.

```json
[
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
      "scansCount": { "$sum": 1 },
      "domain": { "$first": { "$arrayElemAt": ["$userDetails.domain", 0] } }
    }
  },
  { "$sort": { "scansCount": -1 } }
]
```

---

## Database Indexing Configurations

Indexes bypass normal collection scans. Rather than forcing MongoDB to interpret arrays linearly (O(n)), B-Tree indexes yield O(log n) mapping. These are all the indexes created to optimize the database:

- **`files` & `systemArtifacts : ("name", "text")`**: Required for our full-text searching functionality (`{"$text": {"$search"}}`) to operate rapidly across all stored paths in the GUI.
- **`folders` & `systemFolders : ("path", 1)`**: Unique mappings (`unique=True`) guarantee scanner paths are entirely deduplicated seamlessly across disk evaluations.
- **`tags : ("name", 1)`**: Unique mapping to prevent duplicate global tags from being generated.
- **`file_tags : (("fileUid", 1), ("tagId", 1))`**: A unique compound index ensuring the many-to-many join table logic cleanly avoids duplicating tag associations.
- **`accessLog : ("timestamp", -1)`**: Ensures retrieval of scan logs sorting from newest to oldest behaves optimally in the time-series.
- **`trash : ("autoPurgeAt", TTL)`**: Deploys a Time-to-Live (`expireAfterSeconds=0`) automatic MongoDB cronjob ensuring items correctly dump after their lifecycle expires naturally without manual script sweeps.
- **`users : ("username", 1)`**: Configured uniquely (`unique=True`) to prevent parallel user creation mapping errors and significantly optimize `$lookup` joins from the access log.
- **`systemArtifacts : ("uid", 1)`**: Configured uniquely (`unique=True`) enforcing the constraint applied naturally by MongoDB's `ReplaceOne` logic, avoiding duplicated system cache item logs.

---

### Possible Additions With Regards to DSA:

1.  `AVL-tree` (or `Red-Black`) – SIZE INDEX
    - **Use-case**: “Top 100 biggest files”, “everything between 50 MB and 200 MB”
    - **Implementation**:
      - Key = file size (`uint64_t`), value = file UID
      - Insert / delete / update when Watchdog notices a change
      - In-order walk → already sorted, O(log n)
      - Python glue: `top_biggest(100)` returns UIDs in milliseconds without touching Mongo.

2.  `Hash-Table` (`unordered_map`) – PATH → UID CACHE
    - **Use-case**: Watchdog gives us a full path; we need the UID immediately to update / delete
    - **Implementation**:
      - `unordered_map<string, string> pathToUid`
      - Updated on insert / rename / delete
      - O(1) lookup instead of a Mongo query every event

3.  `Graph` + `Dijkstra` – FOLDER SHORTEST PATH
    - **Use-case**: “Move this file to Backup” – suggest shortest folder route
    - **Implementation**:
      - Nodes = folders, edges = parent-child, weight = 1
      - Build adjacency list once (scan phase)
      - Dijkstra gives shortest path; show user a button “Move along 3-folder route”

4.  `Merge-Sort` / `Quick-Sort` – CLIENT-SIDE SORTING
    - **Use-case**: user clicks “Sort by size” or “Sort by date”
    - **Implementation**:
      - Pull UIDs + key from Mongo once, push into `vector<pair<Key, UID>>`
      - Your own `mergeSort()` or `quickSort()` → reorder vector
      - GUI refreshes rows – no extra DB hit
