"""Versions a file. Given a file, adds _v#, where # is the first unused
number not existing already.
"""

import os
import shutil
from datetime import datetime


def version_file_timestamp(filepath):
    """version files with a timestamp for uniqueness"""
    if filepath.startswith("s3://"):
        print("Warning, cannot version files in S3 yet.")
        return
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    versioned_path = f"{filepath}.{timestamp}.bak"
    shutil.move(filepath, versioned_path)


def version_file_numeric(filepath):
    """version files with a simple version number increment"""
    if filepath.startswith("s3://"):
        print("Warning, cannot version files in S3 yet.")
        return

    if not os.path.exists(filepath):
        # print("File does not exist. No need to version.")
        return

    dirname, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)

    version = 1
    while True:
        new_filename = f"{name}_v{version}{ext}"
        new_filepath = os.path.join(dirname, new_filename)
        if not os.path.exists(new_filepath):
            break
        version += 1

    shutil.move(filepath, new_filepath)
    # print(f"File versioned as: {new_filepath}")
