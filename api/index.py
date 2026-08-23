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

    try:
        # 1. 套用背景白化 (與 main.py 邏輯一致)
        img = whiten_background(img)
        
        # 2. 執行影像處理去除筆跡 (與 main.py 一樣跑 5 次以獲得較佳效果)
        for _ in range(5):
            img = process_image(img, color_type=color_type, tolerance=0, fill_method=fill_method)
            
        # 3. 根據選項決定是否增強對比
        if enhance:
            img = enhance_text(img)
            
        # 4. 編碼回 PNG 格式
        is_success, im_buf_arr = cv2.imencode(".png", img)
        if not is_success:
            return jsonify({'error': 'Failed to encode processed image'}), 500
            
        # 5. 回傳圖片
        byte_io = io.BytesIO(im_buf_arr.tobytes())
        byte_io.seek(0)
        return send_file(byte_io, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
