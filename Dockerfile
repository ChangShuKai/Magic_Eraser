FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴，包含 gunicorn 作為正式環境的 WSGI 伺服器
# 同時安裝 onnxruntime 作為高速 CPU 引擎 (取代笨重的 torch)
RUN pip install --no-cache-dir -r requirements.txt gunicorn onnxruntime

# 複製專案原始碼
COPY . .

# 設定環境變數，避免 python 產生 .pyc 並啟用 stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Cloud Run 預設監聽 8080 port
EXPOSE 8080

# 使用 gunicorn 啟動 Flask 應用 (對應 api/index.py 中的 app)
# 設定 threads 可增加併發處理能力
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "api.index:app"]
