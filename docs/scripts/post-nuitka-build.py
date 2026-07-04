import sys

if sys.platform == "win32":
    raise SystemExit(0)

import os
import subprocess


def get_dir_size(folder_path: str) -> int:
    total_size = 0
    # Walk through the directory tree
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Skip broken symbolic links
            if not os.path.islink(file_path):
                total_size += os.path.getsize(file_path)
    return total_size


dist_size = get_dir_size("rovr.dist")
subprocess.run(["find", "rovr.dist", "-name", "*.so*", "-exec", "strip", "{}", "+"])
new_dist_size = get_dir_size("rovr.dist")

print(f"{dist_size / (1024 * 1024):.2f} MB -> {new_dist_size / (1024 * 1024):.2f} MB")
