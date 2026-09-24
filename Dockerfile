FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴，包含 gunicorn 作為正式環境的 WSGI 伺服器
# 同時安裝 onnxruntime 作為高速 CPU 引擎 (取代笨重的 torch)
RUN pip install --no-cache-dir -r requirements.txt gunicorn onnxruntime

# 資安修復：建立非 root 使用者
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 複製專案原始碼
COPY . .

# 確保 .env 不會被打包進映像檔
RUN rm -f .env .env.local .env.production

# 設定目錄權限
RUN chown -R appuser:appuser /app

# 設定環境變數，避免 python 產生 .pyc 並啟用 stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 資安修復：以非 root 使用者身份運行
USER appuser

# Cloud Run 預設監聯 8080 port
EXPOSE 8080

# 使用 gunicorn 啟動 Flask 應用 (對應 api/index.py 中的 app)
# 設定 threads 可增加併發處理能力
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "120", "api.index:app"]
