"""Merge the trained LoRA adapter into a GGUF file that Ollama can serve.

Run in a second Kaggle notebook that has the training notebook attached as an input. It finds
final_adapter on its own, exports a GGUF, and collects the two files you need into
/kaggle/working: the .gguf and a Modelfile, and deletes everything else there, so the
notebook's output download (results.zip) contains only those two files.

Settings (environment variables, all optional): ADAPTER_DIR (a folder with adapter_config.json,
for example a checkpoint-N folder), QUANT (default q4_k_m).
"""

# Unsloth must be imported before transformers and peft.
from unsloth import FastLanguageModel  # isort: skip

import glob
import os
import shutil
from pathlib import Path

QUANT = os.environ.get("QUANT", "q4_k_m")
WORK_DIR = Path("/kaggle/working")
EXPORT_DIR = WORK_DIR / "gguf_export"
MAX_SEQ_LENGTH = 1536

# Qwen2.5 uses the ChatML format. Used only if Unsloth did not write a Modelfile.
FALLBACK_MODELFILE = '''FROM ./{gguf}
TEMPLATE """{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>"""
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0
'''


def find_adapter() -> str:
    """Return the adapter folder: ADAPTER_DIR, else final_adapter found under /kaggle/input."""
    if os.environ.get("ADAPTER_DIR"):
        return os.environ["ADAPTER_DIR"]
    configs = glob.glob("/kaggle/input/**/final_adapter/adapter_config.json", recursive=True)
    if not configs:
        raise FileNotFoundError(
            "final_adapter not found under /kaggle/input; add the training notebook as an input"
        )
    return str(Path(configs[0]).parent)


def collect_deploy_files() -> list[str]:
    """Leave only the .gguf and a Modelfile in /kaggle/working, writing a Modelfile if needed."""
    ggufs = sorted(WORK_DIR.rglob("*.gguf"), key=lambda p: p.stat().st_size)
    if not ggufs:
        raise FileNotFoundError("export finished but no .gguf file was found")
    gguf = ggufs[-1]
    existing = next(iter(WORK_DIR.rglob("Modelfile")), None)
    if existing:
        lines = existing.read_text(encoding="utf-8").splitlines()
        lines = [f"FROM ./{gguf.name}" if ln.startswith("FROM") else ln for ln in lines]
        modelfile_text = "\n".join(lines) + "\n"
    else:
        modelfile_text = FALLBACK_MODELFILE.format(gguf=gguf.name)

    keep = WORK_DIR / ".deploy_staging"
    keep.mkdir()
    shutil.move(str(gguf), keep / gguf.name)
    (keep / "Modelfile").write_text(modelfile_text, encoding="utf-8")
    for item in WORK_DIR.iterdir():
        if item == keep:
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)
    for item in keep.iterdir():
        shutil.move(str(item), WORK_DIR / item.name)
    keep.rmdir()
    return sorted(p.name for p in WORK_DIR.iterdir())


def main() -> None:
    """Export the adapter to GGUF and gather the deployable files."""
    adapter = find_adapter()
    print(f"using adapter at {adapter}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True
    )
    model.save_pretrained_gguf(str(EXPORT_DIR), tokenizer, quantization_method=QUANT)
    print(f"output now contains only: {collect_deploy_files()}")


if __name__ == "__main__":
    main()
