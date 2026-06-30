import os
import argparse

# ==============================================================================
# Face Detection Dataset Downloader
# ==============================================================================
# This script automatically downloads the requested Face Detection datasets 
# locally so you don't have to manually hunt for them.
# 
# Supported Datasets:
# 1. WIDER FACE (Gold Standard Benchmark)
# 2. CelebA (Attributes & Bounding Boxes)
# 3. LFW (Labeled Faces in the Wild)
# 4. FDDB (Face Detection Data Set and Benchmark)
#
# Requirements: pip install datasets torchvision
# ==============================================================================

DOWNLOAD_DIR = "./datasets/face-detection"

def download_huggingface_dataset(dataset_name, config_name=None):
    """Downloads datasets hosted on Hugging Face."""
    try:
        from datasets import load_dataset
        print(f"\n[+] Downloading {dataset_name} from Hugging Face...")
        if config_name:
            dataset = load_dataset(dataset_name, config_name, cache_dir=DOWNLOAD_DIR)
        else:
            dataset = load_dataset(dataset_name, cache_dir=DOWNLOAD_DIR)
        print(f"[SUCCESS] {dataset_name} downloaded successfully to {DOWNLOAD_DIR}!")
        print(dataset)
    except ImportError:
        print("[-] Error: 'datasets' package not found. Run `pip install datasets`")
    except Exception as e:
        print(f"[-] Failed to download {dataset_name}. Error: {e}")

def download_torchvision_dataset(dataset_class_name):
    """Downloads datasets built into PyTorch's torchvision."""
    try:
        import torchvision
        print(f"\n[+] Downloading {dataset_class_name} via Torchvision...")
        
        if dataset_class_name == "CelebA":
            torchvision.datasets.CelebA(root=DOWNLOAD_DIR, split="train", download=True)
        elif dataset_class_name == "WIDERFace":
            torchvision.datasets.WIDERFace(root=DOWNLOAD_DIR, split="train", download=True)
        elif dataset_class_name == "LFWPeople":
            torchvision.datasets.LFWPeople(root=DOWNLOAD_DIR, split="10fold", download=True)
        elif dataset_class_name == "FDDB":
            print("[-] FDDB is best downloaded directly via Kaggle or its official site.")
            return

        print(f"[SUCCESS] {dataset_class_name} downloaded successfully to {DOWNLOAD_DIR}!")
    except ImportError:
        print("[-] Error: 'torchvision' package not found. Run `pip install torchvision`")
    except RuntimeError as e:
        # CelebA and WIDERFace often hit Google Drive download quotas.
        print(f"[-] Download blocked by quota or network error: {e}")
        print("    Try downloading via Kaggle or HuggingFace instead.")
    except Exception as e:
        print(f"[-] Failed to download {dataset_class_name}. Error: {e}")

if __name__ == "__main__":
    print("==========================================================")
    print("      Automated Face Detection Dataset Downloader")
    print("==========================================================")
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # 1. WIDER FACE
    # Hugging Face maintains a reliable mirror of WIDER FACE
    download_huggingface_dataset("wider_face")
    
    # 2. CelebA
    # We can use Hugging Face for CelebA as well since torchvision often fails on GDrive quotas
    download_huggingface_dataset("HuggingFaceM4/CelebA-Faces")
    
    # 3. LFW (Labeled Faces in the Wild)
    download_torchvision_dataset("LFWPeople")
    
    # 4. FDDB & MAFA
    print("\n[i] For FDDB, UTKFace, and MAFA, the most reliable download method is Kaggle.")
    print("    Install kaggle (`pip install kaggle`) and run:")
    print("    - FDDB:  `kaggle datasets download -d klemenko/fddb-face-detection`")
    print("    - UTKFace: `kaggle datasets download -d jangedoo/utkface-new`")
    print("    - MAFA:  `kaggle datasets download -d mafa-dataset-link`")
    
    print(f"\n[DONE] Check your '{DOWNLOAD_DIR}' folder for the downloaded data.")
