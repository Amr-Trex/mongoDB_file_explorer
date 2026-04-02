import subprocess
import os
import pathlib
from pymongo import MongoClient

# Connect to DB
client = MongoClient("mongodb://localhost:27017/")
db = client.fileManager

def get_top_files(k=10):
    """
    Fetches all files from MongoDB, pipes them to the C++ AVL Tree executable,
    and returns the top K largest files as a list of dictionaries.
    """
    
    # 1. Path to C++ executable
    # Assumes run from project root or src/
    # Let's find project root first
    current_dir = pathlib.Path(__file__).parent.resolve()
    project_root = current_dir.parent
    exe_path = project_root / "cpp" / "avl_analytics.exe"

    if not exe_path.exists():
        print(f"Error: C++ Executable not found at {exe_path}")
        return []

    # 2. Prepare Data Stream
    # We construct a large string or generator to feed into stdin
    # Format: UID|NAME|SIZE\n
    cursor = db.files.find({}, {"uid": 1, "name": 1, "size": 1})
    
    input_data = ""
    count = 0
    for doc in cursor:
        uid = doc.get('uid')
        if not uid: continue
        line = f"{uid}|{doc.get('name', 'unknown')}|{doc.get('size', 0)}\n"
        input_data += line
        count += 1
    
    print(f"[Python] Extracted {count} records from MongoDB. Sending to C++ AVL Tree...")

    # 3. Run Subprocess
    try:
        # Popen allows us to send input and capture output
        process = subprocess.Popen(
            [str(exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Handle as text (string), not bytes
        )
        
        # Communicate sends input and waits for process to finish
        stdout, stderr = process.communicate(input=input_data)
        
        if process.returncode != 0:
            print(f"C++ Error: {stderr}")
            return []

        # 4. Parse Output
        # Format: SIZE|NAME|UID
        results = []
        for line in stdout.strip().split("\n"):
            if not line: continue
            parts = line.split("|")
            if len(parts) >= 3:
                results.append({
                    "size": int(parts[0]),
                    "name": parts[1],
                    "uid": parts[2]
                })
        
        return results

    except Exception as e:
        print(f"Execution failed: {e}")
        return []

if __name__ == "__main__":
    print("--- AVL Tree Size Analytics ---")
    top_files = get_top_files(10)
    
    print(f"\nTop {len(top_files)} Largest Files (Sorted by C++):")
    print(f"{'SIZE (bytes)':<15} {'FILENAME':<30} {'UID'}")
    print("-" * 60)
    
    for f in top_files:
        print(f"{f['size']:<15} {f['name']:<30} {f['uid']}")
