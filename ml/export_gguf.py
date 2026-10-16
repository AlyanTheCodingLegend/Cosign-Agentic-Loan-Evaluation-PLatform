"""Merge the trained LoRA adapter into a GGUF file that Ollama can serve.

Paste this into a new cell at the end of the Kaggle notebook (the GPU session must still be
open), or run it with `!python export_gguf.py`. It writes /kaggle/working/gguf/ with a .gguf
file and a Modelfile. Download both, then see "Serve the fine-tune" in the README.

Settings: ADAPTER_DIR (default /kaggle/working/final_adapter, or point at a checkpoint-N folder),
QUANT (default q4_k_m).
"""

# Unsloth must be imported before transformers and peft.
from unsloth import FastLanguageModel  # isort: skip

import os

ADAPTER_DIR = os.environ.get("ADAPTER_DIR", "/kaggle/working/final_adapter")
OUT_DIR = os.environ.get("GGUF_DIR", "/kaggle/working/gguf")
QUANT = os.environ.get("QUANT", "q4_k_m")
MAX_SEQ_LENGTH = 1536

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=ADAPTER_DIR, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True
)
model.save_pretrained_gguf(OUT_DIR, tokenizer, quantization_method=QUANT)
print(f"wrote {OUT_DIR}: {os.listdir(OUT_DIR)}")
