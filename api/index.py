from flask import Flask, request, jsonify, send_file
import cv2
import numpy as np
import io
import sys
import os

# 將父目錄加入 sys.path 以便匯入 image_processor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from image_processor import process_image, enhance_text, whiten_background

app = Flask(__name__)

@app.route('/api/index', methods=['POST'])
def process():
    """處理圖片上傳與轉換的 API (Vercel Serverless Function)"""
    # 1. 驗證 JWT Token (與 Modal 版本相同的資安防護)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401
        
    token = auth_header.split(" ")[1]
    
    import requests
    SUPABASE_URL = "https://qrjkjdlwhmihxkqnrxzu.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFyamtqZGx3aG1paHhrcW5yeHp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc1NDYzMjYsImV4cCI6MjEwMzEyMjMyNn0.Z4VAfv6SIUvibLv5h02Arp9gq3jeCPWwBc_S1zuNUDA"
    
    resp = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY}
    )
    if resp.status_code != 200:
        return jsonify({'error': 'Invalid token or session expired.'}), 401
        
    user_data = resp.json()
    user_id = user_data.get("id")
    
    # 檢查 VIP 狀態
    profile_resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?select=is_vip&id=eq.{user_id}",
        headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY}
    )
    is_vip = False
    if profile_resp.status_code == 200:
        profiles = profile_resp.json()
        if len(profiles) > 0:
            is_vip = profiles[0].get("is_vip", False)
            
    # 頻率限制 (非 VIP 會員每小時 30 張，單機記憶體暫存)
    if not is_vip:
        import time
        if not hasattr(app, 'rate_limits'):
            app.rate_limits = {}
        
        current_hour = int(time.time() // 3600)
        usage_key = f"{user_id}_{current_hour}"
        count = app.rate_limits.get(usage_key, 0)
        
        if count >= 30:
            return jsonify({'error': 'Rate limit exceeded. Free users are limited to 30 images per hour. Please upgrade to SVIP for unlimited access.'}), 429
            
        app.rate_limits[usage_key] = count + 1

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
        
    file = request.files['image']
    color_type = request.form.get('color_type', 'both')
    fill_method = request.form.get('fill_method', 'white')
    enhance_str = request.form.get('enhance', 'false').lower()
    enhance = (enhance_str == 'true')
    
    # 簡單的參數驗證
    if color_type not in ['red', 'blue', 'both']:
        return jsonify({'error': 'Invalid color_type'}), 400
    if fill_method not in ['white', 'inpaint']:
        return jsonify({'error': 'Invalid fill_method'}), 400

    # 讀取圖片到記憶體並轉為 numpy array 給 cv2 使用
    in_memory_file = file.read()
    nparr = np.frombuffer(in_memory_file, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return jsonify({'error': 'Invalid image file'}), 400
        
    # 防禦解壓縮炸彈 / OOM 攻擊 (限制最大邊長為 2048)
    max_dim = 2048
    h, w = img.shape[:2]
    if h > max_dim or w > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    try:
        # 1. 套用背景白化 (與 main.py 邏輯一致)
        img = whiten_background(img)
        
        # 2. 執行影像處理去除筆跡 (與 main.py 一致，只跑 1 次以提升效能)
        img = process_image(img, color_type=color_type, tolerance=50, fill_method=fill_method)
            
        # 3. 根據選項決定是否增強對比
        if enhance:
            img = enhance_text(img)
            
        # 4. 編碼回 JPEG 格式 (大幅減少檔案大小，加速網路傳輸與伺服器處理時間)
        is_success, im_buf_arr = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not is_success:
            return jsonify({'error': 'Failed to encode processed image'}), 500
            
        # 5. 回傳圖片
        byte_io = io.BytesIO(im_buf_arr.tobytes())
        byte_io.seek(0)
        return send_file(byte_io, mimetype='image/jpeg')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
