FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# rapidocr 3.x 不再自帶推論引擎，需另裝 onnxruntime
# fastapi>=0.147 會把未傳的 bool 表單欄位當 False，導致 OCR 三階段全關、回傳空結果
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "rapidocr==3.10.0" onnxruntime "fastapi<0.147"

COPY rapidocr_api ./rapidocr_api

# 建置階段先下載模型，避免容器啟動時才連外下載
RUN python -c "from rapidocr import RapidOCR; RapidOCR()"

EXPOSE 9003

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9003/', timeout=3)"

CMD ["python", "-m", "rapidocr_api.main", "-ip", "0.0.0.0", "-p", "9003", "-workers", "2"]
