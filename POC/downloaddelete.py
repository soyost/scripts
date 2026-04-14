import os
import time

# Specify the path to the Downloads folder
downloads_folder = os.path.expanduser("~/Downloads")

current_time = time.time()
cutoff_time = current_time - (30 * 24 * 60 * 30)  # 30 days in seconds

for filename in os.listdir(downloads_folder):
    file_path = os.path.join(downloads_folder, filename)
    
    # Check if the file is a regular file and its modification time is older than 60 days
    if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
        try:
            os.remove(file_path)
            print(f"Deleted: {filename}")
        except Exception as e:
            print(f"Error deleting {filename}: {str(e)}")

print("Cleanup completed.")
