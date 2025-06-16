python3 -m venv .venv

if [ "$SHELL" = "/usr/bin/fish" ] || [ "$SHELL" = "/bin/fish" ]; then
    source .venv/bin/activate.fish
else
    source .venv/bin/activate
fi

export CMAKE_ARGS="-DGGML_CUDA=OFF"

if command -v nvcc &> /dev/null && [[ "$(uname -m)" != "arm64" && "$(uname)" != "Darwin" ]]; then
    export CMAKE_ARGS="-DGGML_CUDA=ON"
fi

FORCE_CMAKE=1 pip install --upgrade --no-cache-dir -r requirements.txt

deactivate

function download_model {
    mkdir -p "$1"
    wget "$2" -O "$1/model.gguf"
}

download_model models/Llama3_1B_Q8      https://huggingface.co/unsloth/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q8_0.gguf
download_model models/Llama3_3B_Q6      https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q6_K_L.gguf
download_model models/Llama3_8B_Q6      https://huggingface.co/bartowski/Llama-3SOME-8B-v2-GGUF/resolve/main/Llama-3SOME-8B-v2-Q6_K.gguf
download_model models/MistralNemo_8B_Q8 https://huggingface.co/bartowski/Mistral-NeMo-Minitron-8B-Instruct-GGUF/resolve/main/Mistral-NeMo-Minitron-8B-Instruct-Q8_0.gguf
download_model models/Phi2_2B_Q8        https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q6_K.gguf
download_model models/Phi4_3B_Q4        https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
download_model models/TinyLlama1_1B_Q8  https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q8_0.gguf
download_model models/Qwen2_7B_Q8       https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q8_0.gguf
download_model models/Qwen3_14B_Q5      https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q5_K_M.gguf
