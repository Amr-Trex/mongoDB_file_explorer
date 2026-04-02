# C++ File Manager & MongoDB Explanation

This document explains the C++ rewrite of the file manager, focusing on how the C++ application interacts with the MongoDB database to index and search files.

## Architecture Overview

The system consists of three main components:
1.  **MongoDB Database**: Stores metadata about files, folders, and tags.
2.  **Scanner (`scanner.exe`)**: A C++ console application that recursively walks directories, hashes files, and updates the database.
3.  **GUI (`gui.exe`)**: A Qt6 C++ application that queries the database to display files and allows users to open them.

## MongoDB Integration

We use the **mongocxx** driver to communicate with MongoDB.

### Data Schema
The database `fileManager` uses the following collections:

#### 1. `files` Collection
Stores metadata for each file.
-   **_id**: MongoDB Object ID.
-   **uid**: Unique string ID (path hash + timestamp) to track files across scans.
-   **name**: Filename (e.g., `report.pdf`).
-   **ext**: Extension (e.g., `.pdf`).
-   **size**: Size in bytes.
-   **path**: Absolute file path.
-   **folderId**: `_id` of the parent folder in the `folders` collection.
-   **hash**: SHA-256 hash of the file content (for detecting duplicates).

#### 2. `folders` Collection
Stores metadata for directory structure.
-   **path**: Absolute path of the folder (indexed as unique).
-   **name**: Folder name.
-   **owner**: User who owns the folder.

### Indexing Strategy
To ensure performance:
-   `files.name`: **Text Index** for fast search queries.
-   `folders.path`: **Unique Index** to prevent duplicate folder entries.

## Code Logic

### Scanner (`scan.cpp`)
1.  **Connection**: Connects to `mongodb://localhost:27017`.
2.  **Traversal**: Uses `std::filesystem::recursive_directory_iterator` to walk the file tree efficiently.
3.  **Hashing**: Reads files in binary chunks and computes a SHA-256 hash using OpenSSL. keeping memory usage low.
4.  **Upsert Logic**:
    -   It uses `replace_one` with `upsert=true`. roughly translating to: "If this file UID exists, update it; otherwise, insert a new one."
    -   Refreshes metadata like `size` and `modTime` on every scan.

### GUI (`gui.cpp`)
1.  **Qt Structure**: Uses `QTreeWidget` for the table view and `QLineEdit` for search.
2.  **Search**:
    -   When you type and press "Go", it constructs a MongoDB query.
    -   If the search bar is empty: `db.files.find({})` (returns all, limited to 200).
    -   If text exists: `db.files.find({ $text: { $search: "term" } })` uses the full-text index.
3.  **Opening Files**:
    -   Double-clicking an item triggers `QDesktopServices::openUrl()`.
    -   This asks the OS (Windows/Linux/Mac) to open the file with its default application.

## Building the Project
The project uses **CMake**. To build it, you generally run:

```bash
mkdir build
cd build
cmake -DCMAKE_PREFIX_PATH="C:/path/to/qt" ..
cmake --build .
```

Ensure `mongod` is running on the default port (27017) before running the tools.
