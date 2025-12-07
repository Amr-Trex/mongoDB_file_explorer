import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient
import subprocess
import os
import platform


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