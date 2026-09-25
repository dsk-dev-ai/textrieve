FROM python:3.12-slim

WORKDIR /srv

# OpenCV (libGL/libglib) and onnxruntime (libgomp) need these at runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_WAIT_POLICY=PASSIVE \
    TEXTRIEVE_PERMITS=1 \
    PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=10s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=5)" || exit 1

CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1