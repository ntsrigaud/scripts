#!/usr/bin/env python3
"""
Hugging Face Dataset Upload Tool

A robust command-line tool for uploading datasets to Hugging Face Hub
with pre-upload validation, timeout prevention, and incremental batch uploads.

Features:
- Batch-based uploads to prevent timeouts on large datasets
- Real-time progress tracking
- Automatic resume capability
- Timeout risk assessment

Usage:
    python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id username/dataset-name
    python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id username/dataset-name --private
    python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id username/dataset-name --batch-size 500
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional, Set
from collections import defaultdict

import pandas as pd
from huggingface_hub import HfApi, create_repo, whoami, CommitOperationAdd


class DatasetUploader:
    """Validates and uploads datasets to Hugging Face Hub with batch-based incremental uploads."""
    
    # Batch size limits to prevent timeouts
    DEFAULT_BATCH_SIZE_MB = 500  # MB per batch
    DEFAULT_BATCH_FILE_COUNT = 1000  # Max files per batch
    TIMEOUT_WARNING_SIZE_GB = 5  # Warn if single upload exceeds this
    
    def __init__(
        self, 
        dataset_path: Path, 
        repo_id: str, 
        repo_type: str = "dataset", 
        private: bool = False,
        batch_size_mb: Optional[int] = None,
        max_files_per_batch: Optional[int] = None
    ):
        self.dataset_path = Path(dataset_path).resolve()
        self.repo_id = repo_id
        self.repo_type = repo_type
        self.private = private
        self.api = HfApi()
        
        # Batch configuration
        self.batch_size_mb = batch_size_mb or self.DEFAULT_BATCH_SIZE_MB
        self.max_files_per_batch = max_files_per_batch or self.DEFAULT_BATCH_FILE_COUNT
        self.batch_size_bytes = self.batch_size_mb * 1024 * 1024
        
        self.errors = []
        self.warnings = []
        self.uploaded_files: Set[str] = set()  # Track uploaded files for resume
    
    def log_error(self, msg: str):
        """Log a critical error."""
        self.errors.append(msg)
        print(f"❌ ERROR: {msg}")
    
    def log_warning(self, msg: str):
        """Log a warning."""
        self.warnings.append(msg)
        print(f"⚠️  WARNING: {msg}")
    
    def log_info(self, msg: str):
        """Log informational message."""
        print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        """Log success message."""
        print(f"✅ {msg}")
    
    def validate_authentication(self) -> bool:
        """Validate that user is authenticated with Hugging Face."""
        try:
            user_info = whoami()
            self.log_success(f"Authenticated as: {user_info['name']}")
            return True
        except Exception as e:
            self.log_error(f"Not authenticated with Hugging Face: {e}")
            self.log_error("Run: huggingface-cli login")
            return False
    
    def validate_dataset_structure(self) -> bool:
        """Validate dataset directory structure."""
        print("\n" + "="*70)
        print("DATASET STRUCTURE VALIDATION")
        print("="*70)
        
        # Check dataset path exists
        if not self.dataset_path.exists():
            self.log_error(f"Dataset path does not exist: {self.dataset_path}")
            return False
        
        if not self.dataset_path.is_dir():
            self.log_error(f"Dataset path is not a directory: {self.dataset_path}")
            return False
        
        self.log_success(f"Dataset path exists: {self.dataset_path.name}")
        
        # Check README.md
        readme_path = self.dataset_path / "README.md"
        if not readme_path.exists():
            self.log_error("README.md not found at dataset root")
            self.log_error("Hugging Face requires a README.md for dataset card")
            return False
        
        self.log_success("README.md present")
        
        # Check for data directories
        data_dirs = self._find_data_directories()
        if not data_dirs:
            self.log_error("No data directories found (e.g., data/, train/, images/)")
            return False
        
        self.log_success(f"Found data directories: {', '.join(d.name for d in data_dirs)}")
        
        # Validate annotations if present
        if not self._validate_annotations():
            return False
        
        # Check for absolute paths in common annotation files
        if not self._check_path_portability():
            return False
        
        return True
    
    def _find_data_directories(self) -> List[Path]:
        """Find directories that likely contain dataset files."""
        common_data_dirs = ["data", "train", "val", "test", "images", "audio", "video"]
        found_dirs = []
        
        for dir_name in common_data_dirs:
            dir_path = self.dataset_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Check if it contains files
                if any(dir_path.rglob("*")):
                    found_dirs.append(dir_path)
        
        return found_dirs
    
    def _validate_annotations(self) -> bool:
        """Validate annotation files if present."""
        annotation_files = list(self.dataset_path.glob("*.csv")) + list(self.dataset_path.glob("*.json"))
        
        if not annotation_files:
            self.log_info("No annotation files found (optional)")
            return True
        
        print("\nValidating annotation files...")
        
        for ann_file in annotation_files:
            if ann_file.suffix == ".csv":
                if not self._validate_csv_annotations(ann_file):
                    return False
        
        return True
    
    def _validate_csv_annotations(self, csv_path: Path) -> bool:
        """Validate CSV annotation file."""
        try:
            df = pd.read_csv(csv_path)
            self.log_info(f"Loaded {csv_path.name}: {len(df)} entries")
            
            # Check for common path columns
            path_columns = [col for col in df.columns if 'path' in col.lower() or 'file' in col.lower()]
            
            if path_columns:
                # Sample validate paths
                sample_size = min(100, len(df))
                sample_df = df.sample(sample_size) if len(df) > sample_size else df
                
                missing_count = 0
                for col in path_columns:
                    for path_str in sample_df[col].dropna():
                        file_path = self.dataset_path / path_str
                        if not file_path.exists():
                            missing_count += 1
                            if missing_count == 1:  # Show first missing file
                                self.log_error(f"Referenced file not found: {path_str}")
                
                if missing_count > 0:
                    self.log_error(f"Found {missing_count} missing files in {csv_path.name}")
                    return False
                else:
                    self.log_success(f"All sampled paths in {csv_path.name} resolve correctly")
            
            return True
            
        except Exception as e:
            self.log_error(f"Failed to validate {csv_path.name}: {e}")
            return False
    
    def _check_path_portability(self) -> bool:
        """Check that dataset uses relative paths, not absolute."""
        print("\nChecking path portability...")
        
        # Check CSV files for absolute paths
        for csv_file in self.dataset_path.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, nrows=100)
                path_columns = [col for col in df.columns if 'path' in col.lower()]
                
                for col in path_columns:
                    for path_str in df[col].dropna():
                        if Path(path_str).is_absolute():
                            self.log_error(f"Absolute path found in {csv_file.name}: {path_str}")
                            self.log_error("Dataset must use relative paths for portability")
                            return False
            except Exception as e:
                self.log_warning(f"Could not check {csv_file.name}: {e}")
        
        self.log_success("No absolute paths detected (portable)")
        return True
    
    def print_upload_summary(self):
        """Print summary of what will be uploaded."""
        print("\n" + "="*70)
        print("UPLOAD SUMMARY")
        print("="*70)
        
        print(f"\nDataset:     {self.dataset_path.name}")
        print(f"Repository:  {self.repo_id}")
        print(f"Type:        {self.repo_type}")
        print(f"Visibility:  {'Private' if self.private else 'Public'}")
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in self.dataset_path.rglob("*") if f.is_file())
        size_gb = total_size / (1024**3)
        print(f"Total Size:  {size_gb:.2f} GB")
        
        # Count files
        file_count = sum(1 for _ in self.dataset_path.rglob("*") if _.is_file())
        print(f"Total Files: {file_count:,}")
        
        # Estimate batches
        estimated_batches = max(
            (total_size // self.batch_size_bytes) + 1,
            (file_count // self.max_files_per_batch) + 1
        )
        print(f"\n📦 Upload Strategy:")
        print(f"   Batch size:     {self.batch_size_mb} MB")
        print(f"   Max files/batch: {self.max_files_per_batch}")
        print(f"   Estimated batches: {estimated_batches}")
        
        # Timeout risk assessment
        risk_level = self._assess_timeout_risk(total_size, file_count)
        risk_emoji = {"LOW": "✅", "MEDIUM": "⚠️", "HIGH": "🔴"}
        print(f"\n{risk_emoji[risk_level]} Timeout Risk: {risk_level}")
        
        if risk_level == "HIGH":
            print(f"   Large dataset detected ({size_gb:.1f} GB)")
            print(f"   Using incremental batch uploads to prevent timeouts")
        elif risk_level == "MEDIUM":
            print(f"   Moderate dataset size ({size_gb:.1f} GB)")
            print(f"   Batch uploads ensure reliable completion")
        else:
            print(f"   Small dataset ({size_gb:.1f} GB)")
            print(f"   Upload should complete quickly")
        
        print("\nFiles to upload:")
        # List key files
        for item in sorted(self.dataset_path.iterdir()):
            if item.is_file():
                print(f"  📄 {item.name}")
            elif item.is_dir():
                file_count = sum(1 for _ in item.rglob("*") if _.is_file())
                print(f"  📁 {item.name}/ ({file_count:,} files)")
        
        print("="*70)
    
    def _assess_timeout_risk(self, total_size: int, file_count: int) -> str:
        """Assess timeout risk based on dataset characteristics."""
        size_gb = total_size / (1024**3)
        
        if size_gb > 10 or file_count > 10000:
            return "HIGH"
        elif size_gb > 2 or file_count > 2000:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_remote_files(self) -> Set[str]:
        """Get list of files already uploaded to the repository."""
        try:
            files = self.api.list_repo_files(
                repo_id=self.repo_id,
                repo_type=self.repo_type
            )
            return set(files)
        except Exception:
            # Repository doesn't exist or is empty
            return set()
    
    def _batch_files_by_size(self, files: List[Path]) -> List[List[Path]]:
        """Batch files into groups that don't exceed size or count limits."""
        batches = []
        current_batch = []
        current_batch_size = 0
        
        for file_path in sorted(files):
            file_size = file_path.stat().st_size
            
            # Check if adding this file would exceed limits
            if (current_batch and 
                (current_batch_size + file_size > self.batch_size_bytes or
                 len(current_batch) >= self.max_files_per_batch)):
                # Start new batch
                batches.append(current_batch)
                current_batch = []
                current_batch_size = 0
            
            current_batch.append(file_path)
            current_batch_size += file_size
        
        # Add final batch
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _upload_batch(self, batch: List[Path], batch_num: int, total_batches: int, commit_prefix: str) -> bool:
        """Upload a batch of files using create_commit for atomic operation."""
        try:
            # Create commit operations for this batch
            operations = []
            batch_size = 0
            
            for file_path in batch:
                # Calculate path in repo (relative to dataset root)
                path_in_repo = str(file_path.relative_to(self.dataset_path))
                
                # Skip if already uploaded (resume capability)
                if path_in_repo in self.uploaded_files:
                    continue
                
                operations.append(
                    CommitOperationAdd(
                        path_in_repo=path_in_repo,
                        path_or_fileobj=str(file_path)
                    )
                )
                batch_size += file_path.stat().st_size
            
            if not operations:
                self.log_info(f"Batch {batch_num}/{total_batches}: All files already uploaded (skipped)")
                return True
            
            # Show batch progress
            batch_size_mb = batch_size / (1024**2)
            print(f"\n📦 Batch {batch_num}/{total_batches}")
            print(f"   Files: {len(operations)}")
            print(f"   Size: {batch_size_mb:.1f} MB")
            print(f"   Uploading...", end="", flush=True)
            
            start_time = time.time()
            
            # Create commit with all operations in this batch
            self.api.create_commit(
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                operations=operations,
                commit_message=f"{commit_prefix} (batch {batch_num}/{total_batches})"
            )
            
            elapsed = time.time() - start_time
            
            # Mark files as uploaded
            for op in operations:
                self.uploaded_files.add(op.path_in_repo)
            
            print(f" ✅ Complete ({elapsed:.1f}s)")
            self.log_success(f"Batch {batch_num}/{total_batches} committed successfully")
            
            return True
            
        except Exception as e:
            self.log_error(f"Batch {batch_num}/{total_batches} failed: {e}")
            self.log_error(f"Uploaded files preserved. You can resume by running the command again.")
            return False
    
    def create_repository(self) -> bool:
        """Create repository if it doesn't exist."""
        try:
            print(f"\nCreating/verifying repository: {self.repo_id}")
            repo_url = create_repo(
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                private=self.private,
                exist_ok=True
            )
            self.log_success(f"Repository ready: {repo_url}")
            return True
        except Exception as e:
            self.log_error(f"Failed to create repository: {e}")
            return False
    
    def upload_dataset(self) -> bool:
        """Upload dataset files to Hugging Face using incremental batch strategy."""
        print("\n" + "="*70)
        print("UPLOADING DATASET")
        print("="*70)
        
        # Check what's already uploaded (for resume capability)
        print("\n🔍 Checking remote repository state...")
        self.uploaded_files = self._get_remote_files()
        if self.uploaded_files:
            print(f"   Found {len(self.uploaded_files)} files already uploaded")
            print(f"   Will skip already-uploaded files")
        else:
            print(f"   Repository is empty or new")
        
        try:
            # Upload README.md first (small, fast)
            readme_path = self.dataset_path / "README.md"
            readme_in_repo = "README.md"
            
            if readme_in_repo not in self.uploaded_files:
                print("\n📄 Uploading README.md...")
                self.api.upload_file(
                    path_or_fileobj=str(readme_path),
                    path_in_repo=readme_in_repo,
                    repo_id=self.repo_id,
                    repo_type=self.repo_type,
                    commit_message="Upload dataset README"
                )
                self.uploaded_files.add(readme_in_repo)
                self.log_success("README.md uploaded")
            else:
                self.log_info("README.md already uploaded (skipped)")
            
            # Upload annotation files (typically small)
            annotation_files = []
            for pattern in ["*.csv", "*.json", "*.txt"]:
                annotation_files.extend(self.dataset_path.glob(pattern))
            
            for ann_file in annotation_files:
                if ann_file.name == "README.md":
                    continue
                
                ann_in_repo = ann_file.name
                if ann_in_repo not in self.uploaded_files:
                    print(f"\n📊 Uploading {ann_file.name}...")
                    self.api.upload_file(
                        path_or_fileobj=str(ann_file),
                        path_in_repo=ann_in_repo,
                        repo_id=self.repo_id,
                        repo_type=self.repo_type,
                        commit_message=f"Upload {ann_file.name}"
                    )
                    self.uploaded_files.add(ann_in_repo)
                    self.log_success(f"{ann_file.name} uploaded")
                else:
                    self.log_info(f"{ann_file.name} already uploaded (skipped)")
            
            # Upload data directories using batch strategy
            print("\n" + "="*70)
            print("BATCH UPLOAD STRATEGY")
            print("="*70)
            print("\n💡 Large files will be uploaded in batches to prevent timeouts")
            print("💡 Each batch is committed independently for safe resume")
            print("💡 If upload fails, already-uploaded batches are preserved")
            
            data_dirs = self._find_data_directories()
            
            for data_dir in data_dirs:
                print(f"\n" + "="*70)
                print(f"📁 Uploading directory: {data_dir.name}/")
                print("="*70)
                
                # Collect all files in this directory
                all_files = [f for f in data_dir.rglob("*") if f.is_file()]
                total_size = sum(f.stat().st_size for f in all_files)
                total_size_gb = total_size / (1024**3)
                
                print(f"\n📊 Directory Statistics:")
                print(f"   Total files: {len(all_files):,}")
                print(f"   Total size: {total_size_gb:.2f} GB")
                
                # Create batches
                batches = self._batch_files_by_size(all_files)
                print(f"   Batches: {len(batches)}")
                
                # Upload each batch
                for batch_num, batch in enumerate(batches, 1):
                    success = self._upload_batch(
                        batch=batch,
                        batch_num=batch_num,
                        total_batches=len(batches),
                        commit_prefix=f"Upload {data_dir.name}"
                    )
                    
                    if not success:
                        self.log_error(f"Failed to upload batch {batch_num}/{len(batches)}")
                        self.log_error(f"Progress saved. Run again to resume from batch {batch_num}")
                        return False
                
                self.log_success(f"✅ {data_dir.name}/ fully uploaded ({len(batches)} batches)")
            
            return True
            
        except Exception as e:
            self.log_error(f"Upload failed: {e}")
            self.log_error(f"Partial progress may be saved. Run again to resume.")
            return False
    
    def run(self) -> int:
        """Execute the full upload workflow."""
        print("\n" + "="*70)
        print("HUGGING FACE DATASET UPLOADER")
        print("="*70)
        
        # Step 1: Validate authentication
        if not self.validate_authentication():
            return 1
        
        # Step 2: Validate dataset structure
        if not self.validate_dataset_structure():
            print("\n❌ VALIDATION FAILED")
            print("\nErrors found:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            return 1
        
        # Step 3: Print upload summary
        self.print_upload_summary()
        
        # Step 4: Ask for confirmation
        print("\n⚠️  Ready to upload. Continue? [y/N]: ", end="")
        confirmation = input().strip().lower()
        
        if confirmation not in ['y', 'yes']:
            print("\n❌ Upload cancelled by user")
            return 1
        
        # Step 5: Create repository
        if not self.create_repository():
            return 1
        
        # Step 6: Upload dataset
        if not self.upload_dataset():
            return 1
        
        # Step 7: Success
        print("\n" + "="*70)
        print("✅ UPLOAD SUCCESSFUL")
        print("="*70)
        print(f"\n🎉 Dataset uploaded successfully!")
        print(f"\n📊 View your dataset: https://huggingface.co/datasets/{self.repo_id}")
        print(f"\n💡 Load your dataset:")
        print(f"   from datasets import load_dataset")
        print(f"   dataset = load_dataset('{self.repo_id}')")
        print("="*70)
        
        return 0


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Upload datasets to Hugging Face Hub with validation and timeout prevention",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload a public dataset with default batch settings
  python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id username/dataset-name
  
  # Upload a private dataset
  python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id username/dataset-name --private
  
  # Upload with custom batch size (for very large datasets)
  python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id username/dataset-name --batch-size 250
  
  # Upload to an organization
  python upload_dataset_hf.py --dataset_path ./my_dataset --repo_id org-name/dataset-name

Timeout Prevention:
  - Large datasets (>5 GB) are automatically uploaded in batches
  - Each batch is committed independently
  - Progress is preserved if upload is interrupted
  - Simply re-run the command to resume from where it stopped

Requirements:
  - Dataset must have a README.md at the root
  - Dataset must contain at least one data directory (data/, train/, images/, etc.)
  - All paths in annotation files must be relative (not absolute)
  - User must be authenticated: huggingface-cli login
        """
    )
    
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Path to the dataset root directory"
    )
    
    parser.add_argument(
        "--repo_id",
        type=str,
        required=True,
        help="Hugging Face repository ID (e.g., username/dataset-name)"
    )
    
    parser.add_argument(
        "--repo_type",
        type=str,
        default="dataset",
        choices=["dataset", "model", "space"],
        help="Type of repository (default: dataset)"
    )
    
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make the repository private (default: public)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size in MB for incremental uploads (default: 500 MB)"
    )
    
    parser.add_argument(
        "--max-files-per-batch",
        type=int,
        default=1000,
        help="Maximum files per batch (default: 1000)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Create uploader
    uploader = DatasetUploader(
        dataset_path=args.dataset_path,
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        private=args.private,
        batch_size_mb=args.batch_size,
        max_files_per_batch=args.max_files_per_batch
    )
    
    # Run upload workflow
    status_code = uploader.run()
    
    sys.exit(status_code)


if __name__ == "__main__":
    main()
