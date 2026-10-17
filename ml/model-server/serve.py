"""CPU model server: download the fine-tuned GGUF and llama.cpp, then serve an OpenAI-compatible API.

Meant for a build-from-GitHub service on Alternate Clouds, with start command `python serve.py`.
Uses only the standard library. Settings come from environment variables:

    MODEL_URL       required, direct download link to the .gguf (a public Hugging Face file)
    MODEL_ALIAS     name clients put in "model" (default: cosign)
    LLAMA_CPP_TAG   llama.cpp release to use (default: b11701)
    PORT            port to listen on (default: 8000)
    CONTEXT_SIZE    total context tokens shared by all slots (default: 4096)
    PARALLEL        simultaneous requests (default: 2)
"""

import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

WORK_DIR = Path(os.environ.get("WORK_DIR", "/tmp/cosign-model"))
LLAMA_TAG = os.environ.get("LLAMA_CPP_TAG", "b11701")
LLAMA_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/"
    f"llama-{LLAMA_TAG}-bin-ubuntu-x64.tar.gz"
)
CHUNK_BYTES = 1024 * 1024
PROGRESS_EVERY_BYTES = 100 * CHUNK_BYTES


def download(url: str, dest: Path) -> None:
    """Stream url to dest, logging progress. Skips the download if dest already exists."""
    if dest.exists():
        print(f"already have {dest.name}", flush=True)
        return
    partial = dest.with_suffix(dest.suffix + ".part")
    print(f"downloading {url}", flush=True)
    done = next_report = 0
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as out:
        while chunk := response.read(CHUNK_BYTES):
            out.write(chunk)
            done += len(chunk)
            if done >= next_report:
                print(f"  {done // CHUNK_BYTES} MB", flush=True)
                next_report += PROGRESS_EVERY_BYTES
    partial.rename(dest)


def install_llama_server() -> Path:
    """Download and unpack llama.cpp, returning the path of the llama-server binary."""
    target = WORK_DIR / "llama"
    found = next(target.rglob("llama-server"), None) if target.exists() else None
    if found:
        return found
    archive = WORK_DIR / "llama.tar.gz"
    download(LLAMA_URL, archive)
    shutil.rmtree(target, ignore_errors=True)
    with tarfile.open(archive) as tar:
        tar.extractall(target)
    archive.unlink()
    binary = next(target.rglob("llama-server"))
    binary.chmod(0o755)
    return binary


def build_command(binary: Path, model: Path) -> list[str]:
    """Return the llama-server command line."""
    return [
        str(binary),
        "-m", str(model),
        "--alias", os.environ.get("MODEL_ALIAS", "cosign"),
        "--host", "0.0.0.0",
        "--port", os.environ.get("PORT", "8000"),
        "-c", os.environ.get("CONTEXT_SIZE", "4096"),
        "--parallel", os.environ.get("PARALLEL", "2"),
        "-t", str(os.cpu_count() or 4),
        "--chat-template", "chatml",
    ]  # fmt: skip


def main() -> int:
    """Fetch the files and run the server in the foreground."""
    model_url = os.environ.get("MODEL_URL")
    if not model_url:
        print("MODEL_URL is required", file=sys.stderr)
        return 1
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    binary = install_llama_server()
    model = WORK_DIR / "model.gguf"
    download(model_url, model)
    command = build_command(binary, model)
    print("starting:", " ".join(command), flush=True)
    env = {**os.environ, "LD_LIBRARY_PATH": f"{binary.parent}:{os.environ.get('LD_LIBRARY_PATH', '')}"}
    return subprocess.call(command, env=env)


if __name__ == "__main__":
    sys.exit(main())
