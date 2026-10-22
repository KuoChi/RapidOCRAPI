FROM python:3.12-slim-bookworm

# MALLOC_ARENA_MAX：限制 glibc 在多執行緒下建立的 malloc arena 數量，降低峰值與閒置記憶體
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# rapidocr 3.x 不再自帶推論引擎，需另裝 onnxruntime；所有套件版本鎖定在 constraints.txt
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt onnxruntime

COPY rapidocr_api ./rapidocr_api

# 以非 root 使用者執行；程式與套件維持 root 擁有，執行時只需讀取
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001

EXPOSE 9003

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9003/', timeout=3)"

CMD ["python", "-m", "rapidocr_api.main", "-ip", "0.0.0.0", "-p", "9003", "-workers", "1"]
