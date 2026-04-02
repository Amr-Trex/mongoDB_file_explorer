import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient
import subprocess
import os
import platform
<<<<<<< HEAD
=======
import pathlib
from tkinter import filedialog
import scan as scanner_module
import db_commands
import analytics
>>>>>>> ddb3889 (This is the commit for the CPP DSA addition.)


client = MongoClient("mongodb://localhost:27017/")
db   = client.fileManager

# ---------- window ----------
root = tk.Tk()
root.title("File Manager")
root.geometry("700x400")

# ---------- search bar ----------
frm = ttk.Frame(root)
frm.pack(pady=6)
ttk.Label(frm, text="Search:").pack(side="left")
ent = ttk.Entry(frm, width=30)
ent.pack(side="left", padx=6)
btn = ttk.Button(frm, text="Go")
btn.pack(side="left")

<<<<<<< HEAD
=======

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


def show_analytics():
    # 1. Fetch data from C++ Engine
    try:
        top_files = analytics.get_top_files(15)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to run C++ Analytics:\n{e}")
        return

    if not top_files:
        messagebox.showinfo("Analytics", "No files found or C++ engine returned empty.")
        return

    # 2. Show in new window
    win = tk.Toplevel(root)
    win.title("Top 15 Largest Files (AVL Tree Sorted)")
    win.geometry("600x400")

    # Grid
    cols = ("size", "name", "uid")
    tree_a = ttk.Treeview(win, columns=cols, show="headings")
    tree_a.heading("size", text="Size (Bytes)")
    tree_a.heading("name", text="File Name")
    tree_a.heading("uid", text="UID")
    
    tree_a.column("size", width=100, anchor="e")
    tree_a.column("name", width=300)
    tree_a.column("uid", width=150)
    
    tree_a.pack(fill="both", expand=True)

    # Populate
    for f in top_files:
        tree_a.insert("", "end", values=(f"{f['size']:,}", f['name'], f['uid']))


refresh_btn = ttk.Button(toolbar, text=" ↻ Refresh", command=refresh)
refresh_btn.pack(side="left", padx=2)

scan_btn = ttk.Button(toolbar, text="Scan 🔭", command=scan)
scan_btn.pack(side="left", padx=2)

scan_all_btn = ttk.Button(toolbar, text="Scan ALL 🔭", command=lambda: scan(all=True))
scan_all_btn.pack(side="left", padx=2)

clear_btn = ttk.Button(toolbar, text="Clear DB 🗑", command=clearDB)
clear_btn.pack(side="left", padx=2)

analytics_btn = ttk.Button(toolbar, text="Analytics 📊", command=show_analytics)
analytics_btn.pack(side="left", padx=2)



>>>>>>> ddb3889 (This is the commit for the CPP DSA addition.)
# ---------- result grid ----------
cols = ("name", "ext", "size", "folder", "modified")
tree = ttk.Treeview(root, columns=cols, show="headings")
for c in cols:
    tree.heading(c, text=c.title())
    tree.column(c, width=120 if c != "name" else 200)
tree.pack(fill="both", expand=True)

# TODO: understand what tree is over here

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


def search():
    kw = ent.get().strip()
    tree.delete(*tree.get_children())
    if not kw:     # if the search bar is empty
        cursor = db.files.find().limit(200)
    else:
        cursor = db.files.find({"$text": {"$search": kw}}).limit(200)
    
    for doc in cursor:
        folder = db.folders.find_one({"_id": doc["folderId"]}) or {}
        tree.insert("", "end", values=(
            doc["name"],
            doc["ext"],
            f'{doc["size"]:,.0f}',
            folder.get("name", ""),
            doc["dateMod"].strftime("%Y-%m-%d"),
            # doc["path"] 
        ))


tree.bind("<Double-1>", on_open)

btn.config(command=search)
search()  # load all on start
root.mainloop()