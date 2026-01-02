#!/usr/bin/env python3
"""
Organize staging directory into numbered folders for NotebookLM upload order.

Moves files to:
- 01_Master_Knowledge_Base (already done)
- 02_Transcripts (main transcript files, not originals)
- 03_Slide_Images (all PNG files)
- 04_Companion_Files (all slide metadata TXT files)
- 00_Backups (backup transcript files - not for upload)
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
STAGING_DIR = PROJECT_ROOT / "notebooks" / "notebooklm-staging"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

# Folder paths
FOLDER_00 = STAGING_DIR / "00_Backups"
FOLDER_01 = STAGING_DIR / "01_Master_Knowledge_Base"
FOLDER_02 = STAGING_DIR / "02_Transcripts"
FOLDER_03 = STAGING_DIR / "03_Slide_Images"
FOLDER_04 = STAGING_DIR / "04_Companion_Files"


def organize_files():
    """Organize all files in staging directory into numbered folders."""
    
    # Ensure folders exist
    for folder in [FOLDER_00, FOLDER_01, FOLDER_02, FOLDER_03, FOLDER_04]:
        folder.mkdir(exist_ok=True)
        print(f"Ensured folder exists: {folder.name}")
    
    # Counters
    files_moved = {
        "00_Backups": 0,
        "02_Transcripts": 0,
        "03_Slide_Images": 0,
        "04_Companion_Files": 0,
        "skipped": 0,
    }
    
    # Process all files in staging directory root
    for file_path in STAGING_DIR.iterdir():
        # Skip directories (the numbered folders)
        if file_path.is_dir():
            continue
        
        if file_path.is_file():
            filename = file_path.name
            
            # Skip README files (we'll handle those separately)
            if filename == "README.md":
                continue
            
            # Move original transcript backups to backups folder
            if filename.endswith("_transcript_original.txt"):
                dest = FOLDER_00 / filename
                shutil.move(str(file_path), str(dest))
                files_moved["00_Backups"] += 1
                print(f"Moved backup: {filename}")
                continue
            
            # Categorize and move files
            if "_transcript_" in filename and filename.endswith(".txt"):
                # Main transcript files (not backups)
                dest = FOLDER_02 / filename
                shutil.move(str(file_path), str(dest))
                files_moved["02_Transcripts"] += 1
                print(f"Moved transcript: {filename}")
            elif "_slide_" in filename and filename.endswith(".png"):
                # Slide images
                dest = FOLDER_03 / filename
                shutil.move(str(file_path), str(dest))
                files_moved["03_Slide_Images"] += 1
                print(f"Moved slide image: {filename}")
            elif "_slide_" in filename and filename.endswith(".txt"):
                # Companion metadata files
                dest = FOLDER_04 / filename
                shutil.move(str(file_path), str(dest))
                files_moved["04_Companion_Files"] += 1
                print(f"Moved companion file: {filename}")
            elif filename == "Master_Knowledge_Base.md":
                # Master KB should already be in 01 folder, but move if in root
                dest = FOLDER_01 / filename
                if not dest.exists():
                    shutil.move(str(file_path), str(dest))
                    print(f"Moved Master Knowledge Base: {filename}")
            else:
                print(f"Warning: Unclassified file: {filename}")
    
    # Remove individual README files from folders (keep only root README)
    for folder in [FOLDER_01, FOLDER_02, FOLDER_03, FOLDER_04]:
        readme_file = folder / "README.md"
        if readme_file.exists():
            readme_file.unlink()
            print(f"Removed README from {folder.name}/")
    
    # Print summary
    print("\n" + "="*60)
    print("Organization Complete!")
    print("="*60)
    print(f"Backups moved: {files_moved['00_Backups']} (not for upload)")
    print(f"Transcripts moved: {files_moved['02_Transcripts']}")
    print(f"Slide images moved: {files_moved['03_Slide_Images']}")
    print(f"Companion files moved: {files_moved['04_Companion_Files']}")
    
    print("\nUpload order:")
    print("1. 01_Master_Knowledge_Base/ - Upload Master Knowledge Base first")
    print("2. 02_Transcripts/ - Upload all transcript files")
    print("3. 03_Slide_Images/ - Upload all slide images")
    print("4. 04_Companion_Files/ - Upload companion metadata files (optional)")
    print("\nNote: 00_Backups/ contains backup files - do NOT upload these")


if __name__ == "__main__":
    organize_files()
