# HuggingFace Dataset Publishing Toolkit

**Purpose:** Reusable tools for publishing image classification datasets to HuggingFace Hub  
**Status:** Production-ready  
**Last Updated:** January 7, 2026

---

## Overview

This repository contains generic, reusable tooling for preparing and publishing datasets to HuggingFace. It was battle-tested on the HaGRID gesture recognition dataset (24 classes, 19,200 images, 5.8 GB).

### What's Included

- **Upload Script** - Batch-based uploader with timeout prevention
- **Validation Tool** - Pre-upload validation for dataset structure
- **Documentation** - Comprehensive guides and quick references
- **Notebook Examples** - Interactive workflow demonstrations

---

## Quick Start

### 1. Install Dependencies

```bash
pip install huggingface_hub datasets pillow pandas
huggingface-cli login
```

### 2. Prepare Your Dataset

Required structure:
```
my-dataset/
├── README.md              # Dataset card (required)
├── annotations.csv        # Optional metadata
└── data/
    ├── train/
    ├── val/
    └── test/
```

### 3. Upload to HuggingFace

```bash
python scripts/upload_dataset_hf.py \
    --dataset_path /path/to/my-dataset \
    --repo_id username/dataset-name
```

Features:
- ✅ Batch uploads to prevent timeouts
- ✅ Automatic resume on interruption
- ✅ Progress tracking
- ✅ Pre-upload validation

---

## Tools

### Upload Script (`scripts/upload_dataset_hf.py`)

Generic batch-based uploader for large datasets.

**Features:**
- Uploads in configurable batch sizes (default 500 MB)
- Prevents timeouts on large datasets (tested up to 25 GB)
- Resumes automatically if interrupted
- Validates dataset structure before upload

**Usage:**
```bash
python scripts/upload_dataset_hf.py \
    --dataset_path ./my-dataset \
    --repo_id username/dataset-name \
    --batch-size 500 \
    --max-files-per-batch 1000
```

**Options:**
- `--private` - Make repository private
- `--batch-size` - Batch size in MB (default: 500)
- `--max-files-per-batch` - Max files per batch (default: 1000)

### Validation Tool (`scripts/validate_dataset_for_hf.py`)

Pre-upload validator to catch issues before deployment.

**Checks:**
- README.md presence (required by HuggingFace)
- Annotation file validity
- File path resolution
- Label enumeration

**Usage:**
```bash
cd /path/to/my-dataset
python /path/to/scripts/validate_dataset_for_hf.py
```

---

## Documentation

### Comprehensive Guide
📖 **[HUGGINGFACE_PUBLISHING_GUIDE.md](HUGGINGFACE_PUBLISHING_GUIDE.md)**
- Complete step-by-step instructions
- Prerequisites and setup
- Dataset preparation
- Upload strategies
- Troubleshooting

### Quick Reference
⚡ **[HUGGINGFACE_QUICK_REFERENCE.md](HUGGINGFACE_QUICK_REFERENCE.md)**
- Installation commands
- Common operations
- API examples
- Quick troubleshooting

### Interactive Tutorial
📓 **[notebooks/huggingface_dataset_workflow.ipynb](notebooks/huggingface_dataset_workflow.ipynb)**
- Hands-on examples
- Dataset loading patterns
- Visualization techniques

---

## Best Practices

### For Large Datasets (>5 GB)

1. **Use batch uploads** - Default settings handle this automatically
2. **Test with subset first** - Validate with small sample before full upload
3. **Check timeout risk** - Script provides risk assessment before upload
4. **Enable resume** - Script tracks uploaded files for safe resume

### For Multi-Class Datasets (>10 classes)

1. **Explicit label definition** - Don't rely on HuggingFace auto-inference
2. **Create loading script** - Define `ClassLabel` explicitly
3. **Add YAML config** - Include `dataset_info.yaml` with all labels
4. **Enhance README** - Add `dataset_info` to YAML frontmatter

Example loading script:
```python
from datasets import GeneratorBasedBuilder, Features, ClassLabel, Image

class MyDataset(GeneratorBasedBuilder):
    def _info(self):
        return Features({
            'image': Image(),
            'label': ClassLabel(names=[
                'class_1', 'class_2', ..., 'class_n'  # Explicit enumeration
            ])
        })
```

### README.md Requirements

Minimal required frontmatter:
```yaml
---
license: mit
task_categories:
  - image-classification
dataset_info:
  features:
    - name: label
      dtype:
        class_label:
          names:
            - class_1
            - class_2
            # ... list all classes
---
```

---

## Troubleshooting

### "Authentication failed"
```bash
huggingface-cli login
# Paste token from https://huggingface.co/settings/tokens
```

### "Upload timeout"
```bash
# Reduce batch size
python scripts/upload_dataset_hf.py \
    --dataset_path ./my-dataset \
    --repo_id username/dataset-name \
    --batch-size 250
```

### "Only some labels visible on HuggingFace"
- Add explicit loading script (`<dataset-name>.py`)
- Include `dataset_info.yaml` with all labels
- Update README.md frontmatter with `dataset_info`

### "Missing files after upload"
- Check `.gitignore` patterns
- Verify file paths in annotations are relative
- Use validation script before upload

---

## Project History

This toolkit was developed during the publication of the HaGRID gesture recognition subset:
- **Dataset:** 24 gesture classes, 19,200 images (~5.8 GB)
- **Challenge:** Timeout-resistant upload of 19K+ files
- **Solution:** Batch-based incremental uploads with resume capability
- **Result:** Successfully published to HuggingFace with all 24 labels visible

**Published Dataset:** https://huggingface.co/datasets/[username]/hagrid-subset

---

## Repository Structure

```
.
├── README.md                              # This file
├── HUGGINGFACE_PUBLISHING_GUIDE.md        # Comprehensive guide
├── HUGGINGFACE_QUICK_REFERENCE.md         # Quick reference
├── notebooks/
│   └── huggingface_dataset_workflow.ipynb # Interactive examples
└── scripts/
    ├── upload_dataset_hf.py               # Main uploader
    └── validate_dataset_for_hf.py         # Pre-upload validator
```

**Size:** ~120 KB (cleaned and optimized)

---

## License

MIT License - Free to use for any dataset publishing workflow

---

## Contributing

These tools are production-ready and tested on real-world datasets. Contributions welcome for:
- Additional validation checks
- Support for other dataset types (audio, video, text)
- Enhanced progress reporting
- Platform-specific optimizations

---

## Support

For issues or questions:
1. Check [HUGGINGFACE_PUBLISHING_GUIDE.md](HUGGINGFACE_PUBLISHING_GUIDE.md) for detailed instructions
2. Review [HUGGINGFACE_QUICK_REFERENCE.md](HUGGINGFACE_QUICK_REFERENCE.md) for common patterns
3. Run validation script to diagnose issues
4. Consult HuggingFace documentation: https://huggingface.co/docs/datasets

---

**Last Tested:** January 7, 2026  
**HuggingFace Hub API:** 0.28.0+  
**Datasets Library:** Compatible with latest version
