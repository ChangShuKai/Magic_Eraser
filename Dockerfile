FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt
COPY requirements.txt .

# 先安裝 CPU 版本的 PyTorch 與 torchvision (加入 --no-cache-dir 避免 Cloud Build 記憶體不足崩潰)
RUN pip install --no-cache-dir torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu

# 安裝 Python 依賴，包含 gunicorn 作為正式環境的 WSGI 伺服器 (並補上 pillow)
RUN pip install --no-cache-dir -r requirements.txt gunicorn pillow

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
