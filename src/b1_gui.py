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
root.geometry("700x400")
style = ttk.Style()
style.theme_use("clam")  

# ---------- tool bar ----------
bold10 = ("Segoe UI", 10, "bold")
bold12 = ("Segoe UI", 12, "bold")

toolbar = ttk.Frame(root)
toolbar.pack(fill="x", pady=2)

detail_bar = ttk.Frame(root)
detail_bar.pack(fill="x", pady=2)

ttk.Button(toolbar, text=" ⚙  Settings").pack(side="right", padx=2)

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



# ---------- result grid ----------
cols = ("name", "ext", "size", "folder", "modified")
tree = ttk.Treeview(root, columns=cols, show="headings")
for c in cols:
    tree.heading(c, text=c.title())
    tree.column(c, width=120 if c != "name" else 200)
tree.pack(fill="both", expand=True)
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
        style.map("Treeview", background=[("selected", "#0078d7")])
        tree.tag_configure("odd", background="black") # This seems incorrect for light mode, assuming it was a placeholder.
        tree.tag_configure("even", background="white")
        
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
        style.map("Treeview", background=[("selected", "#3e3e3e")])
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


def search():
    # TODO: fix search
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
refresh_counts()
root.mainloop()