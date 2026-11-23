# Build/run only on a Linux NVIDIA CUDA-capable host with NVIDIA Container Toolkit.
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime
WORKDIR /srv
RUN pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' 'pydantic>=2.8,<3' 'transformers>=4.51,<5' 'peft>=0.15,<1' 'accelerate>=1,<2' 'safetensors>=0.5,<1'
COPY ml_service/ /srv/ml_service/
ENV ANNSETU_USE_MODEL=true ANNSETU_BASE_MODEL=Qwen/Qwen3-0.6B ANNSETU_ADAPTER_PATH=/models/annsetu_qwen_adapter
EXPOSE 8100
CMD ["python", "-m", "uvicorn", "ml_service.app:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
