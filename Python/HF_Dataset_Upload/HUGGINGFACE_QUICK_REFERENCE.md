# Hugging Face Publishing - Quick Reference

## ✅ Deliverables Created

1. **[HUGGINGFACE_PUBLISHING_GUIDE.md](HUGGINGFACE_PUBLISHING_GUIDE.md)** - Complete step-by-step guide (70+ sections)
2. **[notebooks/huggingface_dataset_workflow.ipynb](notebooks/huggingface_dataset_workflow.ipynb)** - Interactive Jupyter notebook

---

## Quick Start Commands

### 1. Setup (One-time)
```bash
# Install packages
pip install huggingface_hub datasets pillow pandas torch torchvision

# Authenticate
huggingface-cli login
# Paste your token from: https://huggingface.co/settings/tokens
```

### 2. Upload Dataset (Publisher)
```python
from huggingface_hub import HfApi, create_repo

# Create repository
repo_id = create_repo("hagrid-subset", repo_type="dataset")

# Upload files
api = HfApi()
api.upload_folder(
    folder_path="./hagrid-subset-upload/data",
    path_in_repo="data",
    repo_id="YOUR_USERNAME/hagrid-subset",
    repo_type="dataset"
)
```

### 3. Load Dataset (User)
```python
from huggingface_hub import snapshot_download
import pandas as pd

# Download dataset
dataset_path = snapshot_download(
    repo_id="YOUR_USERNAME/hagrid-subset",
    repo_type="dataset"
)

# Load annotations
df = pd.read_csv(f"{dataset_path}/annotations.csv")
train_df = df[df['split'] == 'train']  # 14,592 samples
val_df = df[df['split'] == 'val']      # 1,728 samples
test_df = df[df['split'] == 'test']    # 2,880 samples
```

### 4. Create PyTorch DataLoader
```python
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

class HaGRIDDataset(Dataset):
    def __init__(self, df, dataset_path, transform=None):
        self.df = df
        self.dataset_path = dataset_path
        self.transform = transform
        self.classes = sorted(df['label'].unique())
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        image = Image.open(f"{self.dataset_path}/{row['image_path']}").convert('RGB')
        label = self.class_to_idx[row['label']]
        if self.transform:
            image = self.transform(image)
        return image, label

# Create dataset
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

train_dataset = HaGRIDDataset(train_df, dataset_path, transform)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
```

---

## Essential URLs

- **Create Token:** https://huggingface.co/settings/tokens
- **Create Dataset:** https://huggingface.co/new-dataset
- **HF Documentation:** https://huggingface.co/docs/datasets

---

## Dataset Specifications

| Property | Value |
|----------|-------|
| **Total Images** | 19,200 |
| **Gesture Classes** | 24 |
| **Samples/Class** | 800 |
| **Train Split** | 14,592 (76%) |
| **Val Split** | 1,728 (9%) |
| **Test Split** | 2,880 (15%) |
| **Image Format** | JPEG |
| **Total Size** | ~5.8 GB |

---

## Gesture Classes (24)

call, dislike, fist, four, grabbing, grip, like, middle_finger, mute, no_gesture, ok, one, palm, peace, peace_inverted, point, rock, stop, stop_inverted, three, three2, three3, two_up, two_up_inverted

---

## Directory Structure for Upload

```
hagrid-subset/
├── README.md              # Dataset card with metadata
├── annotations.csv        # 19,200 entries
└── data/
    ├── train/
    │   ├── call/         (608 images)
    │   ├── dislike/      (608 images)
    │   └── ... (24 gesture folders)
    ├── val/
    │   └── ... (72 images per class)
    └── test/
        └── ... (120 images per class)
```

---

## Troubleshooting

### Issue: Upload too slow
**Solution:** Use `multi_commits=True` in `upload_folder()`

### Issue: "Repository not found"
**Solution:** 
1. Check repository name: `https://huggingface.co/datasets/YOUR_USERNAME/hagrid-subset`
2. Ensure you're authenticated: `huggingface-cli whoami`
3. If private, login first: `huggingface-cli login`

### Issue: Out of disk space
**Solution:** 
```python
snapshot_download(
    repo_id="YOUR_USERNAME/hagrid-subset",
    local_dir="/path/to/larger/disk",
    repo_type="dataset"
)
```

---

## Complete Workflow Example

```python
# === PUBLISHER WORKFLOW ===
from huggingface_hub import HfApi, create_repo

# 1. Prepare dataset locally (already done)
DATASET_PATH = "./hagrid-subset-upload"

# 2. Create repository
create_repo("hagrid-subset", repo_type="dataset", private=False)

# 3. Upload files
api = HfApi()
api.upload_folder(
    folder_path=f"{DATASET_PATH}/data",
    repo_id="YOUR_USERNAME/hagrid-subset",
    path_in_repo="data",
    repo_type="dataset",
    multi_commits=True
)

# === USER WORKFLOW ===
from huggingface_hub import snapshot_download
import pandas as pd
from torch.utils.data import DataLoader

# 1. Download dataset
dataset_path = snapshot_download(
    repo_id="YOUR_USERNAME/hagrid-subset",
    repo_type="dataset"
)

# 2. Load and split
df = pd.read_csv(f"{dataset_path}/annotations.csv")
train_df = df[df['split'] == 'train']

# 3. Create DataLoader (use HaGRIDDataset class above)
train_dataset = HaGRIDDataset(train_df, dataset_path, transform)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

# 4. Start training
for images, labels in train_loader:
    # Your training code
    pass
```

---

## Files Generated

1. **HUGGINGFACE_PUBLISHING_GUIDE.md** - Comprehensive guide with 7 sections
2. **notebooks/huggingface_dataset_workflow.ipynb** - Executable Jupyter notebook
3. **HUGGINGFACE_QUICK_REFERENCE.md** - This file

---

**Last Updated:** January 5, 2026
