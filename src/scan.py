from pymongo import MongoClient, ReplaceOne
import pathlib, os, datetime, hashlib, mimetypes, platform
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


def get_user_and_roles(path):
    """Returns a dictionary with user name and roles based on file permissions."""
    try:
        user_name = os.getlogin()
    except Exception:
        user_name = "unknown"
    
    roles = []
    if os.access(path, os.R_OK):
        roles.append("read")
    if os.access(path, os.W_OK):
        roles.append("write")
    if os.access(path, os.X_OK):
        roles.append("execute")
        
    return user_name, roles

def detect_system_artifact(full_path, fname, ext):
    """
    Returns (is_trash, is_sys, os_origin).
    """
    path_str = str(full_path)
    if "$RECYCLE.BIN" in path_str.upper():
        return True, False, None
    if ".git" in full_path.parts or ext == ".sample":
        return False, True, "Git"
        
    windows_names = {"thumbs.db", "desktop.ini", "ntuser.dat", "pagefile.sys", "hiberfil.sys"}
    windows_exts = {".sys", ".dll", ".tmp", ".bat", ".ini"}
    mac_names = {".ds_store", ".trash"}
    android_names = {".nomedia", ".thumbnails"}
    linux_names = {".bash_history", ".config", ".cache"}
    
    fname_lower = fname.lower()
    
    if fname_lower in windows_names or ext in windows_exts:
        return False, True, "Windows"
    if fname_lower in mac_names:
        return False, True, "MacOS"
    if fname_lower in android_names:
        return False, True, "Android"
    if fname_lower in linux_names or ext in {".cache"}:
        return False, True, "Linux"
    if fname.startswith('.'):
        return False, True, "Generic/Linux"
        
    return False, False, None

def detect_system_folder(folder_path, folder_name):
    path_str = str(folder_path)
    if "$RECYCLE.BIN" in path_str.upper():
        return True
    
    sys_names = {".git", ".vscode", "node_modules", ".idea", "__pycache__"}
    if folder_name in sys_names or folder_name.startswith('.'):
        return True
        
    windows_paths = ["\\AppData\\", "\\Program Files\\", "\\Windows\\", "\\ProgramData\\", "\\Program Files (x86)\\"]
    for w in windows_paths:
        if w.upper() in path_str.upper():
            return True
            
    return False

# -------------------- 6-collection writer --------------------
def scan(root: pathlib.Path, owner="me"):
    ensure_indexes()
    tag_cache = {}        # name -> _id
    user_cache = {}       # username -> _id
    device_name = f"{platform.node()} ({platform.system()}{platform.release()})"

    bulk_trash = []
    bulk_sys = []
    bulk_files = []
    bulk_chunks = []
    bulk_file_tags = []
    bulk_access = []

    def flush_bulks():
        if bulk_trash: db.trash.bulk_write(bulk_trash)
        if bulk_sys: db.systemArtifacts.bulk_write(bulk_sys)
        if bulk_files: db.files.bulk_write(bulk_files)
        if bulk_chunks: db.textChunks.bulk_write(bulk_chunks)
        if bulk_file_tags: db.file_tags.bulk_write(bulk_file_tags)
        if bulk_access: db.accessLog.insert_many(bulk_access, ordered=False)
        bulk_trash.clear(); bulk_sys.clear(); bulk_files.clear()
        bulk_chunks.clear(); bulk_file_tags.clear(); bulk_access.clear()


# ========================================================================================================
    for folder, _, files in os.walk(root):
        folder_path = pathlib.Path(folder).resolve()
        is_sys_folder = detect_system_folder(folder_path, folder_path.name)

        # ________________________1.1. folders collection
        fold_doc = {
            "path": str(folder_path), 
            "name": folder_path.name, 
            "owner": owner,
            "folderType": "sysFolder" if is_sys_folder else "userFolder",
            # date added... for the schema
            "dateAdded": datetime.datetime.now(),
        }
        
        if is_sys_folder:
            db.systemFolders.replace_one({"path": fold_doc["path"]}, fold_doc, upsert=True)
            folder_id = db.systemFolders.find_one({"path": str(folder_path)})["_id"]
            print
        else:
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

            user_name, roles = get_user_and_roles(str(full))
            if user_name not in user_cache:
                user_doc = {
                    "username": user_name,
                    "domain": os.environ.get("USERDOMAIN", "unknown"),
                    "dateAdded": datetime.datetime.now()
                }
                db.users.replace_one({"username": user_name}, user_doc, upsert=True)
                user_cache[user_name] = db.users.find_one({"username": user_name})["_id"]
            user_id = user_cache[user_name]

            ext = full.suffix.lower()
            is_trash, is_sys, os_origin = detect_system_artifact(full, fname, ext)

            if is_trash:
                trash_doc = {
                    "uid": uid,
                    "name": fname,
                    "ext": ext,
                    "size": stat.st_size,
                    "path": str(full),
                    "folderId": folder_id,
                    "deviceName": device_name,
                    "fileType": "TrashFile",
                    "dateDeleted": datetime.datetime.now(),
                    "autoPurgeAt": datetime.datetime.now() + datetime.timedelta(days=30)
                }
                bulk_trash.append(ReplaceOne({"uid": uid}, trash_doc, upsert=True))
                # Add to count check later
            elif is_sys:
                sys_doc = {
                    "uid": uid,
                    "name": fname,
                    "ext": ext,
                    "size": stat.st_size,
                    "path": str(full),
                    "folderId": folder_id,
                    "deviceName": device_name,
                    "osOrigin": os_origin,
                    "fileType": "SystemFile",
                    "dateMod": datetime.datetime.fromtimestamp(stat.st_mtime)
                }
                bulk_sys.append(ReplaceOne({"uid": uid}, sys_doc, upsert=True))
            else:
                # ________________________1.2. files collection ________________________
                file_doc = {
                    "uid": uid,
                    "name": fname,
                    "ext": ext,
                    "size": stat.st_size,
                    "path": str(full),
                    "folderId": folder_id,
                    "owner": owner,
                    "userId": user_id,
                    "roles": roles,
                    "deviceName": device_name,
                    "fileType": "UserFile",
                    "dateAdded": datetime.datetime.now(),
                    "dateMod": datetime.datetime.fromtimestamp(stat.st_mtime),
                    "hash": get_hash(full),
                    "mime": mimetypes.guess_type(str(full))[0] or "unknown"
                }
                bulk_files.append(ReplaceOne({"uid": uid}, file_doc, upsert=True))

                # _____________________2. textChunks (text files only)
            # TODO: I should edit this so that it includes all text AND code file extensions...
                if file_doc["ext"] in {".txt", ".md", ".py", ".cpp", ".java", ".doc", ".docx"}:
                    try:
                        txt = full.read_text(encoding="utf8", errors="ignore")[:4000]
                        bulk_chunks.append(ReplaceOne(
                            {"fileId": uid, "chunkNo": 0},
                            {"fileId": uid, "chunkNo": 0, "text": txt}, upsert=True))

                        # ________________________3. auto-tag by extension  (example)
                        tag_name = "text-file" if file_doc["ext"] in [".txt", ".md", ".doc", ".docx"] else f"code-file-{file_doc['ext'].lstrip('.')}"
                        if tag_name not in tag_cache:
                            db.tags.replace_one({"name": tag_name}, {"name": tag_name, "owner": owner}, upsert=True)
                            tag_cache[tag_name] = db.tags.find_one({"name": tag_name})["_id"]
                        bulk_file_tags.append(ReplaceOne(
                            {"fileUid": uid, "tagId": tag_cache[tag_name]},
                            {"fileUid": uid, "tagId": tag_cache[tag_name]}, upsert=True))
                    except:
                    # TODO: also over here... if it's a different file then decide tag_name
                        pass

            # ________________________4. accessLog  (fake "scanned" action for demo)
            bulk_access.append({
                "fileId": uid,
                "user": owner,
                "action": "SCANNED",
                "timestamp": datetime.datetime.now()
            })

            if len(bulk_files) + len(bulk_sys) + len(bulk_trash) >= 500:
                flush_bulks()

    # Flush any remaining items
    flush_bulks()

    # ________________________5. display final count report
    print("Scan complete.")
    print(get_counts())

if __name__ == "__main__":
    ROOT = pathlib.Path(input("Folder to index: ").strip() or pathlib.Path.home())
    scan(ROOT)