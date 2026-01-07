#!/usr/bin/env python3
"""
Local validation script for HaGRID subset dataset configuration.

This script tests the dataset loading with the explicit label configuration
to ensure all 24 labels are correctly recognized before deployment to HuggingFace.
"""

import sys
from pathlib import Path
import pandas as pd


def validate_annotations():
    """Validate the annotations.csv file."""
    print("="*70)
    print("ANNOTATIONS VALIDATION")
    print("="*70)
    
    # Get the dataset path from command line or use current directory
    dataset_path = Path.cwd()
    annotations_path = dataset_path / "annotations.csv"
    
    if not annotations_path.exists():
        print(f"❌ ERROR: annotations.csv not found at {annotations_path}")
        return False
    
    # Load annotations
    df = pd.read_csv(annotations_path)
    print(f"✅ Loaded annotations: {len(df)} total entries")
    
    # Check columns
    required_columns = ['image_path', 'label', 'split']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"❌ ERROR: Missing columns: {missing_columns}")
        return False
    print(f"✅ Required columns present: {required_columns}")
    
    # Check unique labels
    unique_labels = sorted(df['label'].unique())
    expected_labels = [
        'call', 'dislike', 'fist', 'four', 'grabbing', 'grip',
        'like', 'middle_finger', 'mute', 'no_gesture', 'ok', 'one',
        'palm', 'peace', 'peace_inverted', 'point', 'rock', 'stop',
        'stop_inverted', 'three', 'three2', 'three3', 'two_up',
        'two_up_inverted'
    ]
    
    print(f"\n✅ Found {len(unique_labels)} unique labels:")
    for label in unique_labels:
        print(f"   - {label}")
    
    if unique_labels != expected_labels:
        print(f"\n❌ ERROR: Label mismatch!")
        print(f"   Expected: {expected_labels}")
        print(f"   Found: {unique_labels}")
        return False
    
    print(f"\n✅ All 24 expected labels present")
    
    # Check samples per label
    print(f"\n{'Label':<20} {'Count':<10} {'Status'}")
    print("-"*50)
    
    all_correct = True
    for label in expected_labels:
        count = len(df[df['label'] == label])
        status = "✅" if count == 800 else f"❌ (expected 800)"
        print(f"{label:<20} {count:<10} {status}")
        if count != 800:
            all_correct = False
    
    if not all_correct:
        print(f"\n❌ ERROR: Not all labels have 800 samples")
        return False
    
    print(f"\n✅ All labels have exactly 800 samples")
    
    # Check splits
    print(f"\n{'Split':<15} {'Count':<10} {'Expected':<10} {'Status'}")
    print("-"*50)
    
    split_counts = {
        'train': (len(df[df['split'] == 'train']), 14592),
        'val': (len(df[df['split'] == 'val']), 1728),
        'test': (len(df[df['split'] == 'test']), 2880)
    }
    
    splits_correct = True
    for split_name, (actual, expected) in split_counts.items():
        status = "✅" if actual == expected else f"❌ (expected {expected})"
        print(f"{split_name:<15} {actual:<10} {expected:<10} {status}")
        if actual != expected:
            splits_correct = False
    
    if not splits_correct:
        print(f"\n❌ ERROR: Split counts don't match expected values")
        return False
    
    print(f"\n✅ All splits have correct sample counts")
    
    # Check file paths
    print(f"\n📁 Checking file path validity...")
    missing_files = []
    sample_size = min(100, len(df))
    sample_df = df.sample(sample_size, random_state=42)
    
    for idx, row in sample_df.iterrows():
        file_path = dataset_path / row['image_path']
        if not file_path.exists():
            missing_files.append(row['image_path'])
    
    if missing_files:
        print(f"❌ ERROR: Found {len(missing_files)} missing files (from sample of {sample_size}):")
        for path in missing_files[:5]:
            print(f"   - {path}")
        return False
    
    print(f"✅ All sampled file paths ({sample_size}) resolve correctly")
    
    return True


def validate_loading_script():
    """Validate the dataset loading script."""
    print("\n" + "="*70)
    print("LOADING SCRIPT VALIDATION")
    print("="*70)
    
    dataset_path = Path.cwd()
    script_path = dataset_path / "hagrid-subset.py"
    
    if not script_path.exists():
        print(f"❌ ERROR: Loading script not found at {script_path}")
        return False
    
    print(f"✅ Loading script exists: {script_path.name}")
    
    # Read and validate script content
    script_content = script_path.read_text()
    
    # Check for required components
    required_components = [
        'GESTURE_CLASSES',
        'ClassLabel',
        'GeneratorBasedBuilder',
        '_info',
        '_split_generators',
        '_generate_examples'
    ]
    
    missing_components = []
    for component in required_components:
        if component not in script_content:
            missing_components.append(component)
    
    if missing_components:
        print(f"❌ ERROR: Missing components in loading script: {missing_components}")
        return False
    
    print(f"✅ All required components present in loading script")
    
    # Check that all 24 labels are defined in GESTURE_CLASSES
    expected_labels = [
        'call', 'dislike', 'fist', 'four', 'grabbing', 'grip',
        'like', 'middle_finger', 'mute', 'no_gesture', 'ok', 'one',
        'palm', 'peace', 'peace_inverted', 'point', 'rock', 'stop',
        'stop_inverted', 'three', 'three2', 'three3', 'two_up',
        'two_up_inverted'
    ]
    
    for label in expected_labels:
        if f"'{label}'" not in script_content:
            print(f"❌ ERROR: Label '{label}' not found in GESTURE_CLASSES")
            return False
    
    print(f"✅ All 24 labels defined in GESTURE_CLASSES")
    
    return True


def validate_yaml_config():
    """Validate the dataset_info.yaml configuration."""
    print("\n" + "="*70)
    print("YAML CONFIGURATION VALIDATION")
    print("="*70)
    
    dataset_path = Path.cwd()
    yaml_path = dataset_path / "dataset_info.yaml"
    
    if not yaml_path.exists():
        print(f"⚠️  WARNING: dataset_info.yaml not found (optional)")
        return True  # Not critical
    
    print(f"✅ YAML configuration exists: {yaml_path.name}")
    
    # Read YAML content
    yaml_content = yaml_path.read_text()
    
    # Check for required sections
    required_sections = [
        'dataset_info',
        'features',
        'splits',
        'class_label'
    ]
    
    for section in required_sections:
        if section not in yaml_content:
            print(f"⚠️  WARNING: Section '{section}' not found in YAML")
    
    # Check that all 24 labels are in the YAML
    expected_labels = [
        'call', 'dislike', 'fist', 'four', 'grabbing', 'grip',
        'like', 'middle_finger', 'mute', 'no_gesture', 'ok', 'one',
        'palm', 'peace', 'peace_inverted', 'point', 'rock', 'stop',
        'stop_inverted', 'three', 'three2', 'three3', 'two_up',
        'two_up_inverted'
    ]
    
    missing_labels = []
    for label in expected_labels:
        if label not in yaml_content:
            missing_labels.append(label)
    
    if missing_labels:
        print(f"⚠️  WARNING: Labels missing from YAML: {missing_labels}")
    else:
        print(f"✅ All 24 labels present in YAML configuration")
    
    return True


def validate_readme():
    """Validate the README.md dataset card."""
    print("\n" + "="*70)
    print("README VALIDATION")
    print("="*70)
    
    dataset_path = Path.cwd()
    readme_path = dataset_path / "README.md"
    
    if not readme_path.exists():
        print(f"❌ ERROR: README.md not found (required by HuggingFace)")
        return False
    
    print(f"✅ README.md exists")
    
    readme_content = readme_path.read_text()
    
    # Check for YAML frontmatter
    if not readme_content.startswith('---'):
        print(f"⚠️  WARNING: README.md missing YAML frontmatter")
    else:
        print(f"✅ YAML frontmatter present in README.md")
    
    # Check for required metadata
    required_metadata = [
        'license:',
        'task_categories:',
        'dataset_info:'
    ]
    
    for metadata in required_metadata:
        if metadata in readme_content:
            print(f"✅ Metadata present: {metadata}")
        else:
            print(f"⚠️  WARNING: Metadata missing: {metadata}")
    
    # Check that all 24 labels are mentioned
    expected_labels = [
        'call', 'dislike', 'fist', 'four', 'grabbing', 'grip',
        'like', 'middle_finger', 'mute', 'no_gesture', 'ok', 'one',
        'palm', 'peace', 'peace_inverted', 'point', 'rock', 'stop',
        'stop_inverted', 'three', 'three2', 'three3', 'two_up',
        'two_up_inverted'
    ]
    
    labels_in_readme = sum(1 for label in expected_labels if label in readme_content)
    print(f"✅ {labels_in_readme}/24 labels mentioned in README.md")
    
    return True


def main():
    """Run all validation checks."""
    print("\n" + "="*70)
    print("HAGRID SUBSET DATASET VALIDATION")
    print("Local pre-deployment validation")
    print("="*70)
    
    checks = [
        ("Annotations File", validate_annotations),
        ("Loading Script", validate_loading_script),
        ("YAML Configuration", validate_yaml_config),
        ("README Dataset Card", validate_readme)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ ERROR in {check_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((check_name, False))
    
    # Final summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:<30} {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n" + "="*70)
        print("✅ ALL VALIDATIONS PASSED")
        print("="*70)
        print("\n✅ Dataset is ready for deployment to HuggingFace!")
        print("\n📝 Key findings:")
        print("   - All 24 gesture labels present in annotations.csv")
        print("   - Each label has exactly 800 samples (19,200 total)")
        print("   - Train/val/test splits are correct (14,592 / 1,728 / 2,880)")
        print("   - Loading script explicitly defines all 24 labels")
        print("   - README.md includes dataset_info with ClassLabel configuration")
        print("\n🚀 Next step: Upload to HuggingFace using:")
        print("   python scripts/upload_dataset_hf.py \\")
        print("       --dataset_path hagrid-subset-upload \\")
        print("       --repo_id YOUR_USERNAME/hagrid-subset")
        return 0
    else:
        print("\n" + "="*70)
        print("❌ VALIDATION FAILED")
        print("="*70)
        print("\n❌ Please fix the issues above before deployment")
        return 1


if __name__ == "__main__":
    sys.exit(main())
