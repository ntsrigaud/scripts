#!/usr/bin/env python3
"""
Book Image Organizer and Replacer.

This script scans a target directory for an 'All-books-JPG' folder containing 
converted images. It then iterates through all 'Book-*' subdirectories, matches 
existing files by their base name (stem), copies the compressed JPG into the 
book directory, and cleans up the original uncompressed or HEIC file.
"""

import argparse
import shutil
from pathlib import Path

def organize_images(base_dir: str, source_folder_name: str = "All-books-JPG") -> None:
    """
    Distributes compressed JPGs back into their respective Book-* directories 
    and removes the original non-JPG or uncompressed files.

    Parameters:
        base_dir (str): The root directory containing the Book-* and JPG folders.
        source_folder_name (str): The name of the directory containing the new JPGs.

    Returns:
        None
    """
    base_path = Path(base_dir).resolve()
    source_dir = base_path / source_folder_name

    if not source_dir.is_dir():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return

    # Map all new JPGs by their filename stem (e.g., 'IMG_3699': Path(.../IMG_3699.jpg))
    new_jpgs = {f.stem: f for f in source_dir.glob("*.jpg")}
    
    if not new_jpgs:
        print(f"No JPG files found in '{source_dir}'. Exiting.")
        return

    # Find all directories that match the 'Book-*' pattern
    book_dirs = [d for d in base_path.glob("Book-*") if d.is_dir()]
    
    if not book_dirs:
        print(f"No 'Book-*' directories found in '{base_path}'. Exiting.")
        return

    replaced_count = 0

    for book_dir in book_dirs:
        # Iterate over a list of the directory's contents to avoid mutation issues during deletion
        for old_file in list(book_dir.iterdir()):
            if not old_file.is_file():
                continue

            stem = old_file.stem
            
            # If we have a matching compressed JPG for this file
            if stem in new_jpgs:
                new_jpg_path = new_jpgs[stem]
                target_path = book_dir / new_jpg_path.name
                
                # Copy the compressed JPG into the Book directory
                shutil.copy2(new_jpg_path, target_path)
                
                # If the old file has a different extension (e.g., .HEIC or .heic), delete it
                if old_file.name != target_path.name:
                    old_file.unlink()
                    print(f"✓ Replaced: {old_file.name} -> {target_path.name} (in {book_dir.name})")
                else:
                    print(f"✓ Overwrote: {target_path.name} with compressed version (in {book_dir.name})")
                
                replaced_count += 1

    print(f"\nOperation Complete! Successfully updated {replaced_count} files across {len(book_dirs)} directories.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize converted JPGs into their respective Book directories.")
    parser.add_argument("-d", "--dir", default=".", help="Base directory containing the Book-* folders. Defaults to current directory.")
    parser.add_argument("-s", "--source", default="All-books-JPG", help="Name of the folder containing the compressed JPGs. Defaults to 'All-books-JPG'.")
    
    args = parser.parse_args()
    organize_images(args.dir, args.source)