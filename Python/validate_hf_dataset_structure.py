#!/usr/bin/env python3
"""
Hugging Face Dataset Structure Validation

Validates that the HaGRID subset dataset structure and annotations are correct
and fully compatible with Hugging Face datasets.
"""

import sys
from pathlib import Path
from collections import defaultdict
import pandas as pd


class HFDatasetValidator:
    """Validator for Hugging Face dataset structure and annotations."""
    
    def __init__(self, dataset_root: Path):
        self.dataset_root = Path(dataset_root).resolve()
        self.annotations_path = self.dataset_root / "annotations.csv"
        self.data_dir = self.dataset_root / "data"
        
        self.errors = []
        self.warnings = []
        self.info = []
        
    def log_error(self, msg: str):
        self.errors.append(msg)
        print(f"❌ ERROR: {msg}")
    
    def log_warning(self, msg: str):
        self.warnings.append(msg)
        print(f"⚠️  WARNING: {msg}")
    
    def log_info(self, msg: str):
        self.info.append(msg)
        print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        print(f"✅ {msg}")
    
    def validate_filesystem_structure(self) -> bool:
        """Validate the filesystem directory structure."""
        print("\n" + "="*70)
        print("1. FILESYSTEM STRUCTURE VALIDATION")
        print("="*70)
        
        valid = True
        
        # Check dataset root
        if not self.dataset_root.exists():
            self.log_error(f"Dataset root does not exist: {self.dataset_root}")
            return False
        
        self.log_success(f"Dataset root exists: {self.dataset_root.name}")
        
        # Check data directory
        if not self.data_dir.exists():
            self.log_error(f"data/ directory missing at: {self.data_dir}")
            valid = False
        else:
            self.log_success("data/ directory exists")
        
        # Check split directories
        required_splits = ["train", "val", "test"]
        for split in required_splits:
            split_dir = self.data_dir / split
            if not split_dir.exists():
                self.log_error(f"{split}/ directory missing at: {split_dir}")
                valid = False
            else:
                # Count gesture subdirectories
                gesture_dirs = [d for d in split_dir.iterdir() if d.is_dir()]
                self.log_success(f"data/{split}/ exists with {len(gesture_dirs)} gesture classes")
        
        # Check gesture class consistency across splits
        if valid:
            print("\nChecking gesture class consistency across splits...")
            split_gestures = {}
            for split in required_splits:
                split_dir = self.data_dir / split
                gestures = sorted([d.name for d in split_dir.iterdir() if d.is_dir()])
                split_gestures[split] = set(gestures)
            
            # All splits should have same gesture classes
            train_gestures = split_gestures.get("train", set())
            for split, gestures in split_gestures.items():
                if gestures != train_gestures:
                    missing = train_gestures - gestures
                    extra = gestures - train_gestures
                    if missing:
                        self.log_error(f"{split}/ missing gesture classes: {missing}")
                        valid = False
                    if extra:
                        self.log_error(f"{split}/ has unexpected gesture classes: {extra}")
                        valid = False
            
            if valid:
                self.log_success(f"All splits have consistent {len(train_gestures)} gesture classes")
        
        # Check annotations.csv
        if not self.annotations_path.exists():
            self.log_error(f"annotations.csv missing at: {self.annotations_path}")
            valid = False
        else:
            self.log_success("annotations.csv exists")
        
        return valid
    
    def validate_annotation_paths(self) -> bool:
        """Validate that annotation paths are correct and resolve to existing files."""
        print("\n" + "="*70)
        print("2. ANNOTATION PATH VALIDATION")
        print("="*70)
        
        try:
            df = pd.read_csv(self.annotations_path)
            self.log_success(f"Loaded annotations: {len(df)} entries")
        except Exception as e:
            self.log_error(f"Failed to load annotations.csv: {e}")
            return False
        
        # Check required columns
        required_cols = ["image_path", "label", "split"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            self.log_error(f"Missing required columns: {missing_cols}")
            return False
        
        self.log_success(f"All required columns present: {required_cols}")
        
        # Analyze path structure
        print("\nAnalyzing path structure...")
        sample_paths = df["image_path"].head(10).tolist()
        
        print(f"\nSample paths from annotations.csv:")
        for i, path in enumerate(sample_paths[:3], 1):
            print(f"  {i}. {path}")
        
        # Detect path prefix
        first_path = df["image_path"].iloc[0]
        
        if first_path.startswith("data/"):
            path_prefix = "data/"
            self.log_success("Paths correctly start with 'data/'")
        elif first_path.startswith("hagrid_subset/"):
            path_prefix = "hagrid_subset/"
            self.log_error("Paths start with 'hagrid_subset/' but should start with 'data/'")
            self.log_error("This will cause failures when loading on Hugging Face")
            return False
        elif first_path.startswith("hagrid-subset/"):
            path_prefix = "hagrid-subset/"
            self.log_error("Paths start with 'hagrid-subset/' but should start with 'data/'")
            return False
        else:
            path_prefix = None
            self.log_warning(f"Unexpected path format: {first_path}")
        
        # Validate path resolution
        print("\nValidating path resolution...")
        missing_files = []
        checked_count = 0
        
        for idx, row in df.iterrows():
            img_path = row["image_path"]
            
            # Try to resolve path relative to dataset root
            abs_path = self.dataset_root / img_path
            
            if not abs_path.exists():
                missing_files.append(img_path)
                if len(missing_files) <= 5:  # Store first 5 examples
                    print(f"  ❌ Missing: {img_path}")
                    print(f"      Tried: {abs_path}")
            
            checked_count += 1
            if checked_count % 5000 == 0:
                print(f"  Checked {checked_count:,} paths...")
        
        print(f"\nValidated {len(df):,} paths")
        
        if missing_files:
            self.log_error(f"Found {len(missing_files):,} missing files")
            if len(missing_files) <= 10:
                print("\n  Missing files:")
                for path in missing_files[:10]:
                    print(f"    - {path}")
            return False
        else:
            self.log_success(f"All {len(df):,} annotation paths resolve to existing files")
        
        # Check for duplicates
        duplicates = df[df.duplicated(subset=["image_path"], keep=False)]
        if not duplicates.empty:
            self.log_error(f"Found {len(duplicates)} duplicate path entries")
            return False
        else:
            self.log_success("No duplicate paths found")
        
        return True
    
    def validate_split_consistency(self) -> bool:
        """Validate that split column matches directory structure."""
        print("\n" + "="*70)
        print("3. SPLIT CONSISTENCY VALIDATION")
        print("="*70)
        
        try:
            df = pd.read_csv(self.annotations_path)
        except Exception as e:
            self.log_error(f"Failed to load annotations: {e}")
            return False
        
        valid = True
        inconsistencies = 0
        
        print("\nChecking split consistency...")
        for idx, row in df.iterrows():
            img_path = row["image_path"]
            split = row["split"]
            
            # Extract split from path
            path_parts = Path(img_path).parts
            
            # Path should be: data/SPLIT/gesture/file.jpg
            if len(path_parts) >= 2:
                path_split = path_parts[1]  # Get split from path
                
                if path_split != split:
                    inconsistencies += 1
                    if inconsistencies <= 3:
                        self.log_error(f"Split mismatch: path={img_path}, split_col={split}, path_split={path_split}")
                    valid = False
        
        if inconsistencies > 0:
            self.log_error(f"Found {inconsistencies} split consistency errors")
            return False
        else:
            self.log_success("All splits match their directory paths")
        
        # Validate dataset statistics
        print("\nValidating dataset statistics...")
        
        # Check total count
        expected_total = 19200
        actual_total = len(df)
        if actual_total != expected_total:
            self.log_error(f"Total sample count mismatch: expected {expected_total}, got {actual_total}")
            valid = False
        else:
            self.log_success(f"Total samples correct: {actual_total:,}")
        
        # Check split distribution
        expected_splits = {"train": 14592, "val": 1728, "test": 2880}
        split_counts = df["split"].value_counts().to_dict()
        
        print("\nSplit distribution:")
        for split, expected_count in expected_splits.items():
            actual_count = split_counts.get(split, 0)
            status = "✅" if actual_count == expected_count else "❌"
            print(f"  {split:5s}: {actual_count:,} / {expected_count:,} {status}")
            if actual_count != expected_count:
                self.log_error(f"{split} count mismatch: expected {expected_count}, got {actual_count}")
                valid = False
        
        # Check gesture class count
        n_classes = df["label"].nunique()
        expected_classes = 24
        if n_classes != expected_classes:
            self.log_error(f"Gesture class count mismatch: expected {expected_classes}, got {n_classes}")
            valid = False
        else:
            self.log_success(f"Gesture classes correct: {n_classes}")
        
        # Check samples per class
        label_counts = df["label"].value_counts()
        expected_per_class = 800
        all_balanced = all(count == expected_per_class for count in label_counts.values)
        
        if not all_balanced:
            self.log_error("Classes are not balanced (800 samples each)")
            print("\nPer-class distribution:")
            for label, count in label_counts.sort_index().items():
                status = "✅" if count == expected_per_class else "❌"
                print(f"  {label:20s}: {count:4d} {status}")
            valid = False
        else:
            self.log_success(f"All classes balanced: {expected_per_class} samples each")
        
        return valid
    
    def validate_hf_compatibility(self) -> bool:
        """Validate Hugging Face compatibility."""
        print("\n" + "="*70)
        print("4. HUGGING FACE COMPATIBILITY VALIDATION")
        print("="*70)
        
        valid = True
        
        # Check path format
        try:
            df = pd.read_csv(self.annotations_path)
            first_path = df["image_path"].iloc[0]
            
            if not first_path.startswith("data/"):
                self.log_error(f"Paths must start with 'data/' for HF compatibility")
                self.log_error(f"Current format: {first_path}")
                valid = False
            else:
                self.log_success("Path format compatible with Hugging Face")
        except Exception as e:
            self.log_error(f"Failed to check path format: {e}")
            return False
        
        # Check README.md exists
        readme_path = self.dataset_root / "README.md"
        if not readme_path.exists():
            self.log_warning("README.md not found (recommended for HF dataset card)")
        else:
            self.log_success("README.md present")
        
        # Check relative path portability
        print("\nValidating path portability...")
        
        # Paths should be relative to dataset root, not absolute
        has_absolute = any(Path(p).is_absolute() for p in df["image_path"].head(100))
        if has_absolute:
            self.log_error("Found absolute paths - dataset will not be portable")
            valid = False
        else:
            self.log_success("All paths are relative (portable)")
        
        # Verify paths work from dataset root
        sample_df = df.sample(min(100, len(df)), random_state=42)
        unresolvable = 0
        
        for _, row in sample_df.iterrows():
            path = self.dataset_root / row["image_path"]
            if not path.exists():
                unresolvable += 1
        
        if unresolvable > 0:
            self.log_error(f"{unresolvable} paths cannot be resolved from dataset root")
            valid = False
        else:
            self.log_success("Sample paths resolve correctly from dataset root")
        
        return valid
    
    def generate_report(self) -> int:
        """Generate final validation report."""
        print("\n" + "="*70)
        print("VALIDATION REPORT")
        print("="*70)
        
        print(f"\nDataset: {self.dataset_root}")
        print(f"Annotations: {self.annotations_path.name}")
        
        print("\n" + "-"*70)
        print("SUMMARY")
        print("-"*70)
        
        print(f"\nErrors:   {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Info:     {len(self.info)}")
        
        if self.errors:
            print("\n❌ CRITICAL ERRORS FOUND:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        print("\n" + "-"*70)
        print("VERDICT")
        print("-"*70)
        
        if self.errors:
            print("\n❌ DATASET IS INVALID")
            print("\nThe dataset has critical errors that will prevent correct loading")
            print("on Hugging Face. These issues must be fixed before publication.")
            print("\nRecommended Action:")
            print("  1. Fix annotation path prefixes (should start with 'data/')")
            print("  2. Re-run this validation")
            print("  3. Verify manual loading with sample code")
            return 2
        elif self.warnings:
            print("\n⚠️  DATASET IS CONDITIONALLY VALID")
            print("\nThe dataset structure is correct but has minor warnings.")
            print("It can be used but some improvements are recommended.")
            return 1
        else:
            print("\n✅ DATASET IS FULLY VALID")
            print("\nAll validation checks passed. The dataset is ready for:")
            print("  • Hugging Face publication")
            print("  • Remote loading and training")
            print("  • Distribution to other users")
            return 0
    
    def run_full_validation(self) -> int:
        """Run complete validation suite."""
        print("\n" + "="*70)
        print("HUGGING FACE DATASET STRUCTURE VALIDATION")
        print("="*70)
        print(f"\nTarget: {self.dataset_root}")
        
        # Run all validations
        fs_valid = self.validate_filesystem_structure()
        path_valid = self.validate_annotation_paths()
        split_valid = self.validate_split_consistency()
        hf_valid = self.validate_hf_compatibility()
        
        # Generate report
        return self.generate_report()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate HaGRID dataset structure for Hugging Face compatibility"
    )
    parser.add_argument(
        "--dataset-root",
        type=str,
        default="./hagrid-subset",
        help="Path to dataset root directory"
    )
    
    args = parser.parse_args()
    
    validator = HFDatasetValidator(Path(args.dataset_root))
    status_code = validator.run_full_validation()
    
    sys.exit(status_code)


if __name__ == "__main__":
    main()
