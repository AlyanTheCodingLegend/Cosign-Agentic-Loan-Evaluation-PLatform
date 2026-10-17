#!/bin/sh
# Start Ollama, register the baked-in model under MODEL_TAG, then keep the server in the foreground.
set -eu

MODEL_TAG="${MODEL_TAG:-cosign}"

ollama serve &
server_pid=$!

# Wait for the server to accept commands (up to about 60 seconds).
for _ in $(seq 1 60); do
    if ollama list >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

cd /models
ollama create "$MODEL_TAG" -f Modelfile
echo "model $MODEL_TAG is ready"

wait "$server_pid"
