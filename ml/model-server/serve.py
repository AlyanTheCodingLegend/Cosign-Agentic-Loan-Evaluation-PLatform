"""CPU model server: download the fine-tuned GGUF and llama.cpp, then serve an OpenAI-compatible API.

Meant for a build-from-GitHub service on Alternate Clouds, with start command `python serve.py`.
Uses only the standard library. Settings come from environment variables:

    MODEL_URL       required, direct download link to the .gguf (a public Hugging Face file)
    MODEL_ALIAS     name clients put in "model" (default: cosign)
    LLAMA_CPP_TAG   llama.cpp release to use (default: b11701)
    PORT            port to listen on (default: 8000)
    CONTEXT_SIZE    total context tokens shared by all slots (default: 4096)
    PARALLEL        simultaneous requests (default: 2)
    THREADS         CPU threads (default: the container's CPU limit)

After the server is up it sends one tiny request with the app's system prompt
(system_prompt.txt) so that long fixed prefix is cached, and real requests stay fast.
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

WORK_DIR = Path(os.environ.get("WORK_DIR", "/tmp/cosign-model"))
LLAMA_TAG = os.environ.get("LLAMA_CPP_TAG", "b11701")
LLAMA_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/"
    f"llama-{LLAMA_TAG}-bin-ubuntu-x64.tar.gz"
)
CGROUP_CPU_MAX = Path("/sys/fs/cgroup/cpu.max")
SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "system_prompt.txt"
READY_TIMEOUT_SECONDS = 600
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


def cpu_limit() -> int:
    """Return the CPUs this container may use: THREADS, else the cgroup quota, else all cores."""
    if os.environ.get("THREADS"):
        return int(os.environ["THREADS"])
    try:
        quota, period = CGROUP_CPU_MAX.read_text().split()
        if quota != "max":
            return max(1, round(int(quota) / int(period)))
    except (OSError, ValueError):
        pass
    return os.cpu_count() or 4


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
        "-t", str(cpu_limit()),
        "--chat-template", "chatml",
    ]  # fmt: skip


def warm_up(port: str) -> None:
    """Wait until the server is ready, then cache the app's system prompt with a 1-token request."""
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{base}/health", timeout=5)
            break
        except (urllib.error.URLError, OSError):
            time.sleep(2)
    else:
        print("warm-up skipped: server never became ready", flush=True)
        return
    body = json.dumps(
        {
            "model": os.environ.get("MODEL_ALIAS", "cosign"),
            "max_tokens": 1,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")},
                {"role": "user", "content": "warm-up"},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        f"{base}/v1/chat/completions", body, {"content-type": "application/json"}
    )
    started = time.time()
    try:
        urllib.request.urlopen(request, timeout=600).read()
        print(f"warm-up done in {time.time() - started:.0f}s", flush=True)
    except (urllib.error.URLError, OSError) as exc:
        print(f"warm-up failed: {exc}", flush=True)


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
    env = {
        **os.environ,
        "LD_LIBRARY_PATH": f"{binary.parent}:{os.environ.get('LD_LIBRARY_PATH', '')}",
    }
    server = subprocess.Popen(command, env=env)
    threading.Thread(target=warm_up, args=(os.environ.get("PORT", "8000"),), daemon=True).start()
    return server.wait()


if __name__ == "__main__":
    sys.exit(main())
