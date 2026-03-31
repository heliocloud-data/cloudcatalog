"""GUI for invoking the manifest-catalog updater tools"""

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os
from cloudcatalog.updater.catalog_updater import update_catalog_from_json

# from cloudcatalog.updater.catalog_updater import update_catalog_from_csv


def updater_gui():
    """core GUI functions"""

    def browse_file(var):
        """system default file browser"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            var.set(file_path)

    def on_submit():
        """reads JSON and puts up GUI"""
        json_path_val = json_path_var.get()
        json_updates_val = json_updates_var.get()
        collections_filter_val = filter_var.get().strip() or None
        debug_val = debug_var.get()

        if not json_path_val or not json_updates_val:
            messagebox.showerror("Error", "Both JSON file paths are required.")
            return

        try:
            update_catalog_from_json(
                json_path=json_path_val,
                json_updates=json_updates_val,
                collections_filter=collections_filter_val,
                debug=debug_val,
            )
            messagebox.showinfo("Success", "Catalog updated successfully.")
        except Exception as e:
            messagebox.showerror("Execution Failed", str(e))

    root = tk.Tk()
    root.title("Catalog Updater")

    # Conditionally set default values
    default_json_path = "catalog.json" if os.path.isfile("catalog.json") else ""
    default_json_updates = (
        "catalog_stub.json" if os.path.isfile("catalog_stub.json") else ""
    )

    json_path_var = tk.StringVar(value=default_json_path)
    json_updates_var = tk.StringVar(value=default_json_updates)
    filter_var = tk.StringVar()
    debug_var = tk.BooleanVar(value=True)

    # Layout
    ttk.Label(root, text="Original Catalog (json_path):").grid(
        row=0, column=0, sticky="e"
    )
    ttk.Entry(root, textvariable=json_path_var, width=40).grid(row=0, column=1)
    ttk.Button(root, text="Browse", command=lambda: browse_file(json_path_var)).grid(
        row=0, column=2
    )

    ttk.Label(root, text="Updates File (json_updates):").grid(
        row=1, column=0, sticky="e"
    )
    ttk.Entry(root, textvariable=json_updates_var, width=40).grid(row=1, column=1)
    ttk.Button(root, text="Browse", command=lambda: browse_file(json_updates_var)).grid(
        row=1, column=2
    )

    ttk.Label(root, text="Collections Filter (optional):").grid(
        row=2, column=0, sticky="e"
    )
    ttk.Entry(root, textvariable=filter_var, width=40).grid(row=2, column=1)

    ttk.Checkbutton(root, text="Debug mode", variable=debug_var).grid(
        row=3, column=1, sticky="w"
    )

    ttk.Button(root, text="Update Catalog", command=on_submit).grid(
        row=4, column=1, pady=10
    )

    root.mainloop()


# Run the GUI
if __name__ == "__main__":
    updater_gui()
