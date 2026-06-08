#!/usr/bin/env python3
"""
HEIC to Compressed JPEG Batch Converter.

This script discovers HEIC/HEIF images within a specified input directory,
corrects their orientation based on embedded EXIF flags, and downsamples them 
into optimized, web-ready JPEG images utilizing high-concurrency thread pools.
"""

import os
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps
import pillow_heif

# Register HEIF/HEIC openers natively within Pillow's wrapper infrastructure
pillow_heif.register_heif_opener()

def convert_single_image(heic_path: Path, output_dir: Path, quality: int) -> None:
    """
    Processes a single HEIC file and saves it as a compressed JPEG.

    Extracts raw image buffers from an individual HEIC/HEIF container, normalizes 
    asymmetrical rotation layouts via orientation EXIF tags, transforms color channels 
    to baseline RGB space, and writes the output stream utilizing advanced JPEG compression.

    Parameters:
        heic_path (Path): Structural system path referencing the source HEIC image file.
        output_dir (Path): Destination folder path where the JPEG product will be written.
        quality (int): JPEG export quality scale factor ranging from 1 (worst) to 95 (best).

    Returns:
        None
    """
    try:
        # Establish the destination filepath matching the source file's stem name
        jpg_path = output_dir / f"{heic_path.stem}.jpg"
        
        with Image.open(heic_path) as img:
            # Transpose according to EXIF data (fixes upside down/rotated iPhone images)
            img = ImageOps.exif_transpose(img)
            
            # Ensure output is explicitly RGB before saving to JPEG
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Save using advanced JPEG parameters to minimize file size overhead
            img.save(
                jpg_path, 
                "JPEG", 
                quality=quality, 
                optimize=True, 
                progressive=True
            )
        print(f"✓ Converted: {heic_path.name} -> {jpg_path.name}")
    except Exception as e:
        print(f"✗ Failed to convert {heic_path.name}: {str(e)}")

def process_directory(input_dir: str, output_dir: str, quality: int) -> None:
    """
    Orchestrates batch conversion of HEIC images inside a target folder.

    Scans the provided directory path for valid HEIC/HEIF extensions, maps the files
    into an isolated runtime index array, provisions a ThreadPoolExecutor stack to maximize 
    CPU core throughput, and handles file directory generation dynamically if missing.

    Parameters:
        input_dir (str): Relative or absolute path targeting the source asset folder.
        output_dir (str): Destination folder path. Defaults to a subfolder if set to None.
        quality (int): Compression quality integer applied across the entire processing queue.

    Returns:
        None
    """
    in_path = Path(input_dir)
    out_path = Path(output_dir) if output_dir else in_path / "converted_jpgs"
    
    if not in_path.is_dir():
        print(f"Error: Input directory context '{input_dir}' does not exist.")
        return

    # Create the output directory if it doesn't exist
    out_path.mkdir(parents=True, exist_ok=True)

    # Gather case-insensitive target HEIC/HEIF extensions
    extensions = ('*.heic', '*.HEIC', '*.heif', '*.HEIF')
    heic_files = []
    for ext in extensions:
        heic_files.extend(in_path.glob(ext))

    if not heic_files:
        print(f"No valid HEIC/HEIF image containers discovered inside: {in_path.resolve()}")
        return

    print(f"Found {len(heic_files)} files. Compressing and converting via thread pool...")

    # Distribute operations asynchronously to optimize processing times
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(convert_single_image, file, out_path, quality) 
            for file in heic_files
        ]
        # Wait for all operations to finish completely
        for future in futures:
            future.result()

    print(f"\nProcessing Complete! Outputs saved to: {out_path.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert an image directory from HEIC to Compressed JPG.")
    parser.add_argument("-i", "--input", required=True, help="Path to directory containing input HEIC files")
    parser.add_argument("-o", "--output", default=None, help="Path to destination directory (Defaults to an inline subdirectory)")
    parser.add_argument("-q", "--quality", type=int, default=75, help="JPEG compression quality scale: 1 (worst) to 95 (best). Default is 75.")
    
    args = parser.parse_args()
    process_directory(args.input, args.output, args.quality)
