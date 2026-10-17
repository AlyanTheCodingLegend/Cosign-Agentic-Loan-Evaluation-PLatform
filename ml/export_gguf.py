"""Merge the trained LoRA adapter into a GGUF file that Ollama can serve.

Run in a second Kaggle notebook that has the training notebook attached as an input. It finds
final_adapter on its own, exports a GGUF, and collects the two files you need into
/kaggle/working/deploy/: the .gguf and a Modelfile. Download only that folder.

Settings (environment variables, all optional): ADAPTER_DIR (a folder with adapter_config.json,
for example a checkpoint-N folder), QUANT (default q4_k_m), MODEL_TAG (default cosign).
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
DEPLOY_DIR = WORK_DIR / "deploy"
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
    """Copy the .gguf and a Modelfile into deploy/, writing a fallback Modelfile if needed."""
    ggufs = sorted(WORK_DIR.rglob("*.gguf"), key=lambda p: p.stat().st_size)
    ggufs = [g for g in ggufs if DEPLOY_DIR not in g.parents]
    if not ggufs:
        raise FileNotFoundError("export finished but no .gguf file was found")
    gguf = ggufs[-1]
    DEPLOY_DIR.mkdir(exist_ok=True)
    shutil.copy(gguf, DEPLOY_DIR / gguf.name)
    existing = next(iter(WORK_DIR.rglob("Modelfile")), None)
    modelfile_text = (
        existing.read_text(encoding="utf-8")
        if existing
        else FALLBACK_MODELFILE.format(gguf=gguf.name)
    )
    if existing and "FROM" in modelfile_text:
        lines = modelfile_text.splitlines()
        lines = [f"FROM ./{gguf.name}" if ln.startswith("FROM") else ln for ln in lines]
        modelfile_text = "\n".join(lines) + "\n"
    (DEPLOY_DIR / "Modelfile").write_text(modelfile_text, encoding="utf-8")
    return sorted(p.name for p in DEPLOY_DIR.iterdir())


def main() -> None:
    """Export the adapter to GGUF and gather the deployable files."""
    adapter = find_adapter()
    print(f"using adapter at {adapter}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True
    )
    model.save_pretrained_gguf(str(EXPORT_DIR), tokenizer, quantization_method=QUANT)
    print(f"download these from /kaggle/working/deploy: {collect_deploy_files()}")


if __name__ == "__main__":
    main()
