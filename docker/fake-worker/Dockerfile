FROM python:3.13-slim

COPY docker/fake-worker/worker.py /worker.py
WORKDIR /workspace

CMD ["python", "/worker.py"]
