"""Download BGE model files for the semantic encoder."""
import urllib.request
import os

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

FILES = {
    "bge-small-en-v1.5.onnx": "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/onnx/model.onnx",
    "bge-small-en-v1.5-tokenizer.json": "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/tokenizer.json",
}

for filename, url in FILES.items():
    dest = os.path.join(MODEL_DIR, filename)
    if os.path.exists(dest):
        print(f"Already exists: {dest}")
        continue
    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"  Saved: {dest} ({size_mb:.1f} MB)")

print("\nDone. Model files ready in models/")
