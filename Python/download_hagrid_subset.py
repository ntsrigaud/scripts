#!/usr/bin/env python3
"""
HaGRID Subset Downloader and Extractor

This script downloads and extracts a manageable subset of the HaGRID dataset
for gesture recognition training, keeping total size under 1-3GB.

Usage:
    python scripts/download_hagrid_subset.py \
        --save_path ./data/hagrid_subset \
        --gestures call dislike fist like ok palm peace point rock \
        --samples_per_class 800 \
        --download_annotations

Features:
    - Selective download of specific gesture classes
    - Random stratified sampling (maintains train/val/test ratio)
    - Generates simplified folder-per-class structure for PyTorch
    - Creates CSV annotation file for easy loading
    - Progress tracking and size estimation
"""

import argparse
import json
import os
import random
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.request import urlretrieve

import pandas as pd
from tqdm import tqdm

# HaGRID dataset URLs
V2_URL = "https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid_v2/"
MAIN_URL = "https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid/hagrid_dataset_new_554800/"

# All available gestures and their URLs
# HaGRID v2 has 24 gesture classes total
GESTURE_URLS = {
    # Main dataset gestures
    "call": f"{MAIN_URL}hagrid_dataset/call.zip",
    "dislike": f"{MAIN_URL}hagrid_dataset/dislike.zip",
    "fist": f"{MAIN_URL}hagrid_dataset/fist.zip",
    "four": f"{MAIN_URL}hagrid_dataset/four.zip",
    "like": f"{MAIN_URL}hagrid_dataset/like.zip",
    "mute": f"{MAIN_URL}hagrid_dataset/mute.zip",
    "ok": f"{MAIN_URL}hagrid_dataset/ok.zip",
    "palm": f"{MAIN_URL}hagrid_dataset/palm.zip",
    "peace": f"{MAIN_URL}hagrid_dataset/peace.zip",
    "peace_inverted": f"{MAIN_URL}hagrid_dataset/peace_inverted.zip",
    "stop": f"{MAIN_URL}hagrid_dataset/stop.zip",
    "stop_inverted": f"{MAIN_URL}hagrid_dataset/stop_inverted.zip",
    "three": f"{MAIN_URL}hagrid_dataset/three.zip",
    "three2": f"{MAIN_URL}hagrid_dataset/three2.zip",
    "two_up": f"{MAIN_URL}hagrid_dataset/two_up.zip",
    "two_up_inverted": f"{MAIN_URL}hagrid_dataset/two_up_inverted.zip",
    
    # V2 dataset gestures
    "one": f"{V2_URL}hagrid_v2_zip/one.zip",
    "rock": f"{V2_URL}hagrid_v2_zip/rock.zip",
    "grabbing": f"{V2_URL}hagrid_v2_zip/grabbing.zip",
    "grip": f"{V2_URL}hagrid_v2_zip/grip.zip",
    "point": f"{V2_URL}hagrid_v2_zip/point.zip",
    "middle_finger": f"{V2_URL}hagrid_v2_zip/middle_finger.zip",
    "three3": f"{V2_URL}hagrid_v2_zip/three3.zip",
    "no_gesture": f"{V2_URL}hagrid_v2_zip/no_gesture.zip",
}

# These gestures do NOT exist in HaGRID dataset
# If you need them, you'll have to use a different dataset or collect your own
UNAVAILABLE_GESTURES = [
    "holy", "timeout", "xsign", "hand_heart", "hand_heart2", 
    "little_finger", "take_picture", "three_gun", "thumb_index", "thumb_index2"
]

ANNOTATIONS_URL = f"{V2_URL}annotations_with_landmarks/annotations.zip"

# Default recommended gestures (from screenshot + no_gesture)
DEFAULT_GESTURES = [
    "call", "dislike", "fist", "like", "ok", "palm", "peace", "point", "rock", "no_gesture"
]


def list_available_gestures():
    """Print all available gestures in HaGRID dataset."""
    print("\n" + "="*60)
    print("Available HaGRID Gestures (24 total)")
    print("="*60)
    gestures = sorted(GESTURE_URLS.keys())
    for i, gesture in enumerate(gestures, 1):
        print(f"{i:2d}. {gesture}")
    print("="*60)
    return gestures


def download_file(url: str, dest: Path, desc: str = "Downloading"):
    """Download a file with progress bar."""
    def progress_hook(block_num, block_size, total_size):
        if hasattr(progress_hook, 'pbar'):
            progress_hook.pbar.update(block_size)
        else:
            progress_hook.pbar = tqdm(
                total=total_size, unit='B', unit_scale=True, desc=desc
            )
            progress_hook.pbar.update(block_size)
    
    try:
        urlretrieve(url, dest, reporthook=progress_hook)
        if hasattr(progress_hook, 'pbar'):
            progress_hook.pbar.close()
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def download_annotations(save_path: Path) -> Path:
    """Download and extract annotations."""
    ann_dir = save_path / "annotations"
    ann_dir.mkdir(parents=True, exist_ok=True)
    
    ann_zip = save_path / "annotations.zip"
    
    if not ann_zip.exists():
        print("📥 Downloading annotations...")
        success = download_file(ANNOTATIONS_URL, ann_zip, "Annotations")
        if not success:
            raise RuntimeError("Failed to download annotations")
    
    print("📦 Extracting annotations...")
    with zipfile.ZipFile(ann_zip, 'r') as zip_ref:
        zip_ref.extractall(ann_dir)
    
    # Check if annotations were extracted to nested directory
    nested_ann = ann_dir / "annotations"
    if nested_ann.exists() and nested_ann.is_dir():
        print("📁 Moving annotations from nested directory...")
        # Move contents up one level
        for item in nested_ann.iterdir():
            shutil.move(str(item), str(ann_dir / item.name))
        nested_ann.rmdir()
    
    return ann_dir


def load_annotations(ann_dir: Path, split: str, gesture: str) -> Dict:
    """Load annotation JSON for a specific split and gesture."""
    ann_file = ann_dir / split / f"{gesture}.json"
    if not ann_file.exists():
        # Try alternative paths
        alt_paths = [
            ann_dir / "annotations" / split / f"{gesture}.json",
            ann_dir / f"{split}_{gesture}.json",
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                ann_file = alt_path
                break
        else:
            print(f"⚠️  Warning: Annotation file not found: {ann_file}")
            return {}
    
    try:
        with open(ann_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading annotations from {ann_file}: {e}")
        return {}


def sample_images_from_annotations(
    annotations: Dict, 
    n_samples: int, 
    seed: int = 42
) -> List[str]:
    """Randomly sample N image IDs from annotations."""
    image_ids = list(annotations.keys())
    if len(image_ids) <= n_samples:
        return image_ids
    
    random.seed(seed)
    return random.sample(image_ids, n_samples)


def extract_subset_from_zip(
    zip_path: Path,
    gesture: str,
    sampled_ids: Dict[str, List[str]],
    output_dir: Path
) -> List[Tuple[str, str, str]]:
    """
    Extract only sampled images from a gesture ZIP file.
    
    Returns:
        List of (image_path, gesture_label, split) tuples
    """
    extracted_items = []
    
    # Collect all sampled IDs across splits
    all_sampled = set()
    for split, ids in sampled_ids.items():
        all_sampled.update(ids)
    
    print(f"📦 Extracting {len(all_sampled)} images from {gesture}.zip...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.namelist()
        
        # Filter to only images in our sample
        to_extract = []
        for member in members:
            if member.endswith('.jpg') or member.endswith('.jpeg') or member.endswith('.png'):
                # Extract image ID from path (remove extension)
                img_id = Path(member).stem
                if img_id in all_sampled:
                    to_extract.append(member)
        
        # Extract with progress bar
        for member in tqdm(to_extract, desc=f"Extracting {gesture}"):
            zip_ref.extract(member, output_dir)
            
            # Determine split based on which sampled_ids dict contains this ID
            img_id = Path(member).stem
            split = None
            for s, ids in sampled_ids.items():
                if img_id in ids:
                    split = s
                    break
            
            # Move to output structure: output_dir/split/gesture/image.jpg
            src = output_dir / member
            dest = output_dir / split / gesture / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            
            extracted_items.append((str(dest), gesture, split))
    
    # Clean up any empty directories
    for root, dirs, files in os.walk(output_dir, topdown=False):
        for d in dirs:
            dir_path = Path(root) / d
            if not any(dir_path.iterdir()):
                dir_path.rmdir()
    
    return extracted_items


def create_subset_dataset(
    save_path: Path,
    gestures: List[str],
    samples_per_class: int,
    download_annotations_flag: bool = True,
    seed: int = 42
):
    """
    Main function to create a subset dataset.
    
    Args:
        save_path: Root directory for the subset dataset
        gestures: List of gesture classes to include
        samples_per_class: Number of images per class (distributed across splits)
        download_annotations_flag: Whether to download annotations
        seed: Random seed for reproducibility
    """
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    
    # Validate gestures FIRST before downloading anything
    invalid_gestures = [g for g in gestures if g not in GESTURE_URLS]
    if invalid_gestures:
        print(f"\n⚠️  WARNING: The following gestures are not available in HaGRID:")
        for g in invalid_gestures:
            print(f"   - {g}")
        if any(g in UNAVAILABLE_GESTURES for g in invalid_gestures):
            print(f"\n   Note: These gestures don't exist in HaGRID dataset.")
            print(f"   Available gestures: {', '.join(sorted(GESTURE_URLS.keys()))}")
        
        response = input("\n   Continue with only valid gestures? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
        
        gestures = [g for g in gestures if g in GESTURE_URLS]
        print(f"\n   Proceeding with {len(gestures)} valid gestures: {', '.join(gestures)}")
    
    if not gestures:
        print("❌ No valid gestures to download.")
        return
    
    # Step 1: Download annotations
    if download_annotations_flag:
        ann_dir = download_annotations(save_path)
    else:
        ann_dir = save_path / "annotations"
        if not ann_dir.exists():
            raise RuntimeError("Annotations not found. Use --download_annotations flag.")
    
    # Step 2: For each gesture, sample images and download/extract
    all_items = []
    
    for gesture in gestures:
        print(f"\n{'='*60}")
        print(f"Processing gesture: {gesture.upper()}")
        print(f"{'='*60}")
        
        # Load annotations for all splits
        sampled_ids = {}
        total_available = 0
        
        for split in ['train', 'val', 'test']:
            annotations = load_annotations(ann_dir, split, gesture)
            total_available += len(annotations)
            
            # Determine samples for this split (maintain approximate ratio)
            split_ratios = {'train': 0.76, 'val': 0.09, 'test': 0.15}
            n_samples = int(samples_per_class * split_ratios[split])
            
            # Sample
            sampled = sample_images_from_annotations(annotations, n_samples, seed)
            sampled_ids[split] = sampled
            
            print(f"  {split}: sampled {len(sampled)} / {len(annotations)} images")
        
        print(f"  Total available: {total_available}")
        print(f"  Total sampled: {sum(len(ids) for ids in sampled_ids.values())}")
        
        # Download gesture ZIP if not already present
        gesture_zip = save_path / f"{gesture}.zip"
        
        if not gesture_zip.exists():
            print(f"📥 Downloading {gesture}.zip...")
            url = GESTURE_URLS[gesture]
            success = download_file(url, gesture_zip, f"Downloading {gesture}")
            if not success:
                print(f"⚠️  Skipping {gesture} due to download failure")
                continue
        
        # Extract subset from ZIP
        extracted = extract_subset_from_zip(
            gesture_zip, gesture, sampled_ids, save_path
        )
        all_items.extend(extracted)
        
        # Clean up ZIP to save space (optional)
        # gesture_zip.unlink()
    
    # Step 3: Create CSV annotation file for easy loading
    print("\n📝 Creating annotation CSV...")
    df = pd.DataFrame(all_items, columns=['image_path', 'label', 'split'])
    csv_path = save_path / "annotations.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\n✅ Dataset creation complete!")
    print(f"   Total images: {len(df)}")
    print(f"   Classes: {len(gestures)}")
    print(f"   Train: {len(df[df['split']=='train'])}")
    print(f"   Val: {len(df[df['split']=='val'])}")
    print(f"   Test: {len(df[df['split']=='test'])}")
    print(f"   Annotations saved to: {csv_path}")
    
    # Estimate size
    total_size = sum(f.stat().st_size for f in save_path.rglob('*.jpg'))
    print(f"   Total size: {total_size / (1024**3):.2f} GB")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download and create a subset of the HaGRID dataset",
        epilog="Use --list-gestures to see all available gesture classes"
    )
    parser.add_argument(
        "--save_path",
        type=str,
        default="./data/hagrid_subset",
        help="Path to save the subset dataset"
    )
    parser.add_argument(
        "--gestures",
        nargs="+",
        default=DEFAULT_GESTURES,
        help="List of gestures to include in the subset (use --list-gestures to see options)"
    )
    parser.add_argument(
        "--samples_per_class",
        type=int,
        default=800,
        help="Number of images per class (will be distributed across train/val/test)"
    )
    parser.add_argument(
        "--download_annotations",
        action="store_true",
        help="Download annotations (required for first run)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--list-gestures",
        action="store_true",
        dest="list_gestures",
        help="List all available gestures and exit"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Handle --list-gestures flag
    if args.list_gestures:
        list_available_gestures()
        sys.exit(0)
    
    print("="*60)
    print("HaGRID Subset Downloader")
    print("="*60)
    print(f"Save path: {args.save_path}")
    print(f"Gestures: {', '.join(args.gestures)}")
    print(f"Samples per class: {args.samples_per_class}")
    print(f"Estimated total images: {len(args.gestures) * args.samples_per_class}")
    print(f"Estimated size: ~{len(args.gestures) * args.samples_per_class * 3.5 / 1024:.2f} GB")
    print("="*60)
    
    try:
        create_subset_dataset(
            save_path=Path(args.save_path),
            gestures=args.gestures,
            samples_per_class=args.samples_per_class,
            download_annotations_flag=args.download_annotations,
            seed=args.seed
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
