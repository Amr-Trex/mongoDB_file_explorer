import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient
import subprocess
import os
import platform
import pathlib
from tkinter import filedialog
import scan as scanner_module
import db_commands


client = MongoClient("mongodb://localhost:27017/")
db   = client.fileManager

# ---------- window ----------
root = tk.Tk()
root.title("AmrTino's File Manager")
root.geometry("800x500")
style = ttk.Style()
style.theme_use("clam")  

# ---------- tool bar ----------
bold10 = ("Segoe UI", 10, "bold")
bold12 = ("Segoe UI", 12, "bold")

toolbar = ttk.Frame(root)
toolbar.pack(fill="x", pady=2)

detail_bar = ttk.Frame(root)
detail_bar.pack(fill="x", pady=2)

# ttk.Button(toolbar, text=" ⚙  Settings").pack(side="right", padx=2)

# just some button styling
style.configure("Tool.TButton", font=bold10, padding=1.5)
style.map("Tool.TButton", background=[("active", "#e1e1e1")])

# ---------- search bar ----------
frm = ttk.Frame(root)
frm.pack(pady=4)
ttk.Label(frm, text="Search:").pack(side="left", padx=2)
ent = ttk.Entry(frm, width=30)
ent.pack(side="left", padx=6)
btn = ttk.Button(frm, text="Go")
btn.pack(side="left")


# ---------- scan, clear, refresh button ----------
def refresh_counts():
    for c in detail_bar.winfo_children():
        c.destroy()
    counts = db_commands.get_counts()
    for c in counts:
        btn = ttk.Label(detail_bar, text=f"{c}: {counts[c]}")
        btn.pack(side="left", padx=7)


def refresh():
    ent.delete(0, "end")
    refresh_counts()
    search()


def scan(all = False):
    if not all:
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            try:
                # Run the scan
                scanner_module.scan(pathlib.Path(folder_selected))
                messagebox.showinfo("Scan", "Scan Complete!")
                refresh()
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during scanning (here): {e}")
    else:
        if not messagebox.askyesno("Confirm", "Are you sure you want to scan the entire system?"):
            return
        try:
            # Run the scan
            scanner_module.scan(pathlib.Path("/"))
            messagebox.showinfo("Scan", "Scan Complete!")
            refresh()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during scanning (here): {e}")


def clearDB():
    if not messagebox.askyesno("Confirm", "Are you sure you want to clear the database?"):
        return

    db_commands.clear_db()
    messagebox.showinfo("Clear", "Database cleared!")
    refresh()


refresh_btn = ttk.Button(toolbar, text=" ↻ Refresh", command=refresh)
refresh_btn.pack(side="left", padx=2)

scan_btn = ttk.Button(toolbar, text="Scan 🔭", command=scan)
scan_btn.pack(side="left", padx=2)

scan_all_btn = ttk.Button(toolbar, text="Scan ALL 🔭", command=lambda: scan(all=True))
scan_all_btn.pack(side="left", padx=2)

clear_btn = ttk.Button(toolbar, text="Clear DB 🗑", command=clearDB)
clear_btn.pack(side="left", padx=2)

show_system_var = tk.BooleanVar(value=False)
sys_chk = ttk.Checkbutton(toolbar, text="Show System Files", variable=show_system_var, command=lambda: search())
sys_chk.pack(side="left", padx=10)

show_dupes_var = tk.BooleanVar(value=False)
dupes_chk = ttk.Checkbutton(toolbar, text="Find Duplicates", variable=show_dupes_var, command=lambda: search())
dupes_chk.pack(side="left", padx=5)

def open_analytics():
    top = tk.Toplevel(root)
    top.title("Analytics Dashboard")
    top.geometry("600x500")
    
    # Run pipelines
    disk_usage = list(db.files.aggregate(db_commands.get_aggregate("disk_usage_by_extension")))
    user_metrics = list(db.accessLog.aggregate(db_commands.get_aggregate("user_access_metrics")))
    
    ttk.Label(top, text="Disk Usage by Extension", font=bold12).pack(pady=10)
    
    # Table 1
    cols1 = ("Extension", "Total Size (Bytes)", "File Count")
    tree1 = ttk.Treeview(top, columns=cols1, show="headings", height=8)
    for c in cols1: tree1.heading(c, text=c)
    tree1.pack(fill="x", padx=10)
    
    for row in disk_usage:
        ext_val = row.get("_id") or "Unknown"
        size_val = f"{row.get('totalSize', 0):,.0f}"
        count_val = row.get("count", 0)
        tree1.insert("", "end", values=(ext_val, size_val, count_val))
        
    ttk.Label(top, text="User Access Metrics", font=bold12).pack(pady=10)
    
    # Table 2
    cols2 = ("User", "Domain", "Total Scans")
    tree2 = ttk.Treeview(top, columns=cols2, show="headings", height=8)
    for c in cols2: tree2.heading(c, text=c)
    tree2.pack(fill="x", padx=10)
    
    for row in user_metrics:
        user_val = row.get("_id") or "Unknown"
        domain_val = row.get("domain", "Unknown")
        scans_val = row.get("scansCount", 0)
        tree2.insert("", "end", values=(user_val, domain_val, scans_val))

analytics_btn = ttk.Button(toolbar, text="Analytics 📈", command=open_analytics)
analytics_btn.pack(side="right", padx=10)

# ---------- result grid ----------
tree_frame = ttk.Frame(root)
tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

cols = ("name", "ext", "size", "folder", "modified")
tree = ttk.Treeview(tree_frame, columns=cols, show="headings")

scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
tree.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
tree.pack(side="left", fill="both", expand=True)

for c in cols:
    tree.heading(c, text=c.title())
    tree.column(c, width=120 if c != "name" else 200)

tree.tag_configure("odd", background="black")
tree.tag_configure("even", background="white")
tree.tag_configure("selected", background="#0078d7", foreground="white")

# TODO: understand what tree is over here



# ---------- dark mode ----------

is_dark_mode = False
def toggle_dark():
    # @AI Generated
    global is_dark_mode
    if is_dark_mode:
        # Switch to Light Mode
        style.theme_use("clam")
        root.config(bg="#f0f0f0")
        
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", foreground="black")
        style.configure("TEntry", fieldbackground="white", foreground="black")
        style.configure("TButton", background="#e1e1e1", foreground="black")
        style.configure("Tool.TButton", background="#e1e1e1", foreground="black")
        style.map("Tool.TButton", background=[("active", "#d5d5d5")])
        
        style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
        style.configure("Treeview.Heading", background="#e1e1e1", foreground="black", relief="flat")
        style.map("Treeview", background=[("selected", "#0078d7")])
        style.map("Treeview.Heading", background=[("active", "#d2d2d2")])
        tree.tag_configure("odd", background="white")
        tree.tag_configure("even", background="#f9f9f9")
        
        is_dark_mode = False
    else:
        # Switch to Dark Mode
        style.theme_use("clam") # Clam theme is a good base for custom styling
        root.config(bg="#2b2b2b") # Dark background for the root window

        # Configure general widget styles for dark mode
        style.configure("TFrame", background="#2b2b2b")
        style.configure("TLabel", background="#2b2b2b", foreground="white")
        style.configure("TEntry", fieldbackground="#3a3a3a", foreground="white", insertbackground="white")
        style.configure("TButton", background="#505050", foreground="white")
        style.map("TButton", background=[("active", "#606060")])

        # Configure specific toolbar button style for dark mode
        style.configure("Tool.TButton", background="#505050", foreground="white")
        style.map("Tool.TButton", background=[("active", "#606060")])

        # Configure Treeview specific styles for dark mode
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", background="#3a3a3a", foreground="white", relief="flat")
        style.map("Treeview", background=[("selected", "#3e3e3e")])
        style.map("Treeview.Heading", background=[("active", "#4a4a4a")])
        tree.tag_configure("odd", background="#3e3e3e")
        tree.tag_configure("even", background="#2b2b2b")

        is_dark_mode = True

ttk.Button(toolbar, text=" 🌙 ", command=toggle_dark).pack(side="right", padx=6)



# ---------- helpers ----------

def on_open(event):
    # identify the region we clicked on
    # and open the file/folder
    region = tree.identify("region", event.x, event.y)
    if region != "heading" and region != "cell":   # make sure we clicked a row
        return
    col = tree.identify_column(event.x)            # "#1" … "#4"
    selected = tree.selection()
    if not selected:
        return
    item = tree.item(selected[0])["values"]
    file_name  = item[0]      # name column
    folder_name= item[3]      # folder column
    folder_doc = db.folders.find_one({"name": folder_name})
    if not folder_doc:
        messagebox.showerror("Open", "Folder record not found")
        return

    if col == "#4":                       # ******* FOLDER COLUMN ********
        full_path = folder_doc["path"]
    else:                                 # ******* ANY OTHER COLUMN → FILE ********
        full_path = os.path.join(folder_doc["path"], file_name)

    try:
        if platform.system() == "Windows":
            os.startfile(full_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", full_path])
        else:  # Linux
            subprocess.call(["xdg-open", full_path])
    except Exception as e:
        messagebox.showerror("Open", f"Could not open:\n{e}")


current_offset = 0

def load_more_data():
    global current_offset
    kw = ent.get().strip()
    limit = 100
    
    # if show_system_var is true, show system files, else show user files
    collection = db.systemArtifacts if show_system_var.get() else db.files
    filter_doc = {"fileType": "SystemFile"} if show_system_var.get() else {"fileType": "UserFile"}
        
    if show_dupes_var.get():
        cursor = collection.aggregate(db_commands.get_aggregate("find_duplicates"))
    elif not kw:
        cursor = collection.find(filter_doc).skip(current_offset).limit(limit)
    else:
        # imported the pipeline from db_commands.py
        pipeline = db_commands.get_aggregate(
            "search_files",
            search_kw=kw,
            filter_doc=filter_doc,
            offset=current_offset,
            limit=limit
        )
        cursor = collection.aggregate(pipeline)
        
    count = 0
    for result in cursor:
        doc = result.get("files", [result])[0] if show_dupes_var.get() else result
        
        count += 1
        folder = db.folders.find_one({"_id": doc.get("folderId")}) or db.systemFolders.find_one({"_id": doc.get("folderId")}) or {}
        date_mod = doc.get("dateMod")
        date_str = date_mod.strftime("%Y-%m-%d") if date_mod else ""
        
        tree.insert("", "end", values=(
            doc.get("name", ""),
            doc.get("ext", ""),
            f'{doc.get("size", 0):,.0f}',
            folder.get("name", ""),
            date_str
        ))
    
    current_offset += count

def search():
    global current_offset
    current_offset = 0
    tree.delete(*tree.get_children())
    load_more_data()


# scroll and mousewheel event handlers created by AI:
def on_scroll(*args):
    tree.yview(*args)
    if tree.yview()[1] >= 0.95:
        load_more_data()

scrollbar.config(command=on_scroll)
def on_mousewheel(event):
    if tree.yview()[1] >= 0.95 and event.delta < 0:
        load_more_data()
tree.bind("<MouseWheel>", on_mousewheel)


tree.bind("<Double-1>", on_open)

btn.config(command=search)
search()  # load all on start
refresh_counts()
root.mainloop()