import os
import subprocess

import modal

MODEL = "Qwen/Qwen2.5-32B-Instruct"
SERVED_NAME = "qwen"
PORT = 8000
MINUTES = 60

image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)

app = modal.App("collusion-monitor")


@app.function(
    image=image,
    gpu="H200",
    scaledown_window=10 * MINUTES,
    timeout=60 * MINUTES,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    secrets=[modal.Secret.from_name("vllm-key")],
)
@modal.concurrent(max_inputs=16)
@modal.web_server(port=PORT, startup_timeout=20 * MINUTES)
def serve():
    cmd = [
        "vllm", "serve", MODEL,
        "--served-model-name", SERVED_NAME,
        "--host", "0.0.0.0", "--port", str(PORT),
        "--max-model-len", "8192",
        "--api-key", os.environ["VLLM_API_KEY"],
    ]
    subprocess.Popen(cmd)
