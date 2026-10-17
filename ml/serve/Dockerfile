# Model server: Ollama with the fine-tuned model baked in.
# Put model.gguf and Modelfile (from the Kaggle export notebook) in this folder, then see
# "Serve the model on Alternate Clouds" in ml/README.md. Neither file is committed.
FROM ollama/ollama:0.40.5

WORKDIR /models
COPY *.gguf ./
COPY Modelfile ./
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENV OLLAMA_HOST=0.0.0.0:11434
EXPOSE 11434
ENTRYPOINT ["/entrypoint.sh"]
