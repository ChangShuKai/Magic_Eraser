from flask import Flask, request, jsonify, send_from_directory, send_file, Response
import cv2
import numpy as np
import io
import os
from image_processor import process_image, enhance_text, whiten_background

import torch
import torchvision.transforms as T
import torch.nn.functional as F
from PIL import Image

AI_MODELS = {}

def get_ai_model(model_name):
    global AI_MODELS
    if model_name in AI_MODELS:
        return AI_MODELS[model_name]
    
    import sys
    train_pipeline_dir = os.path.join(os.path.dirname(__file__), 'train_pipeline')
    if train_pipeline_dir not in sys.path:
        sys.path.append(train_pipeline_dir)
        
    try:
        from model import MobileNetV3UNet
    except ImportError:
        return None
        
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = MobileNetV3UNet()
    
    if model_name == 'klareo-1-pro':
        model_path = os.path.join(train_pipeline_dir, "checkpoints", "model_epoch_126.pth")
    else:
        # Default for klareo-1-flash or others, you could use a different path
        # Let's find the latest model for flash or just use model_epoch_1.pth
        import glob
        checkpoint_dir = os.path.join(train_pipeline_dir, "checkpoints")
        pth_files = glob.glob(os.path.join(checkpoint_dir, "model_epoch_*.pth"))
        
        # fallback to the 126 or max
        model_path = os.path.join(train_pipeline_dir, "checkpoints", "model_epoch_1.pth")
        if pth_files:
            def get_epoch_num(f):
                try:
                    return int(os.path.basename(f).replace("model_epoch_", "").replace(".pth", ""))
                except:
                    return -1
            latest_pth = max(pth_files, key=get_epoch_num)
            if latest_pth:
                model_path = latest_pth
                
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    
    AI_MODELS[model_name] = (model, device, model_path)
    return AI_MODELS[model_name]

# 建立 Flask 應用程式，並將 public 設定為靜態檔案目錄
app = Flask(__name__, static_folder='public')

# 限制上傳檔案大小為 30MB
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

# 安全標頭中介軟體
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

def is_valid_image_bytes(data: bytes) -> bool:
    """檢查是否為合法的 JPG, PNG 或 WebP 影像魔術字節"""
    if not data or len(data) < 12:
        return False
    if data[:3] == b'\xff\xd8\xff':
        return True
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return True
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return True
    return False

@app.route('/')
def index():
    """回傳首頁 index.html"""
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_files(path):
    """回傳其他靜態檔案 (如 app.js, css 等)"""
    return app.send_static_file(path)

@app.route('/api/process', methods=['POST'])
@app.route('/api-proxy/clean', methods=['POST'])
def process():
    """處理圖片上傳與轉換的 API"""
    is_protobuf = request.headers.get('Content-Type') == 'application/x-protobuf'

    if is_protobuf:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), 'public'))
        import magic_eraser_pb2
        req_msg = magic_eraser_pb2.ProcessRequest()
        try:
            req_msg.ParseFromString(request.data)
        except Exception as e:
            return jsonify({'error': 'Invalid Protobuf data'}), 400
        
        in_memory_file = req_msg.image_data
        color_type = req_msg.color_type or 'both'
        fill_method = req_msg.fill_method or 'white'
        enhance = req_msg.enhance
        model_name = getattr(req_msg, 'model_name', 'klareo-1-flash')
    else:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
            
        file = request.files['image']
        color_type = request.form.get('color_type', 'both')
        fill_method = request.form.get('fill_method', 'white')
        enhance_str = request.form.get('enhance', 'false').lower()
        enhance = (enhance_str == 'true')
        model_name = request.form.get('model_name', 'klareo-1-flash')
        in_memory_file = file.read()

    # 魔術字節驗證：確保上傳內容為真實圖片
    if not is_valid_image_bytes(in_memory_file):
        return jsonify({'error': '不支援的檔案類型或檔案已損毀。僅接受 JPG, PNG, WebP。'}), 415
    
    # 簡單的參數驗證
    if color_type not in ['red', 'blue', 'both']:
        return jsonify({'error': 'Invalid color_type'}), 400
    if fill_method not in ['white', 'inpaint']:
        return jsonify({'error': 'Invalid fill_method'}), 400

    # 讀取圖片到記憶體並轉為 numpy array 給 cv2 使用
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
        if fill_method == 'white':
            # 1. 套用背景白化 (與 main.py 邏輯一致)
            img = whiten_background(img)
            
            # 2. 執行影像處理去除筆跡 (與 main.py 一致，只跑 1 次以提升效能)
            img = process_image(img, color_type=color_type, tolerance=50, fill_method=fill_method)
                
            # 3. 根據選項決定是否增強對比
            if enhance:
                img = enhance_text(img)
                
            # 4. 編碼回 JPEG 格式
            is_success, im_buf_arr = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not is_success:
                return jsonify({'error': 'Failed to encode processed image'}), 500
        else:
            # AI 智慧修補 (inpaint)
            model_info = get_ai_model(model_name)
            if model_info is None:
                return jsonify({'error': 'AI model is not available.'}), 500
                
            model, device, used_model_path = model_info
            
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert("L")
            transform = T.ToTensor()
            input_tensor = transform(img_pil).unsqueeze(0).to(device)
            
            _, _, h_t, w_t = input_tensor.size()
            pad_h = (32 - (h_t % 32)) % 32
            pad_w = (32 - (w_t % 32)) % 32
            if pad_h > 0 or pad_w > 0:
                input_tensor = F.pad(input_tensor, (0, pad_w, 0, pad_h), mode='reflect')
                
            with torch.no_grad():
                if device == 'cuda':
                    with torch.autocast(device_type="cuda", dtype=torch.float16):
                        output_tensor = model(input_tensor)
                else:
                    output_tensor = model(input_tensor)
                    
            if pad_h > 0 or pad_w > 0:
                output_tensor = output_tensor[:, :, :h_t, :w_t]
                
            output_tensor = output_tensor.squeeze(0).clamp(0, 1).cpu()
            out_img = T.ToPILImage()(output_tensor).convert("RGB")
            
            img = cv2.cvtColor(np.array(out_img), cv2.COLOR_RGB2BGR)
            is_success, im_buf_arr = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not is_success:
                return jsonify({'error': 'Failed to encode processed image'}), 500
            
            used_model_name = os.path.basename(used_model_path)
            
        # 5. 回傳圖片
        if is_protobuf:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), 'public'))
            import magic_eraser_pb2
            if fill_method == 'white':
                res_msg = magic_eraser_pb2.ProcessResponse(success=True, image_data=im_buf_arr.tobytes())
            else:
                res_msg = magic_eraser_pb2.ProcessResponse(success=True, image_data=im_buf_arr.tobytes(), used_model_name=used_model_name)
            return Response(res_msg.SerializeToString(), mimetype='application/x-protobuf')
        else:
            byte_io = io.BytesIO(im_buf_arr.tobytes())
            byte_io.seek(0)
            
            # Since send_file doesn't easily support custom headers for file download in a standard way that matches json response, 
            # we can inject a header.
            response = send_file(byte_io, mimetype='image/jpeg')
            if fill_method != 'white':
                response.headers['X-Used-Model-Name'] = used_model_name
            return response
        
    except Exception as e:
        # M-4 修復：不洩漏內部錯誤細節
        import logging
        logging.error(f"Image processing error: {e}", exc_info=True)
        return jsonify({'error': '圖片處理失敗，請稍後再試。'}), 500

if __name__ == '__main__':
    # 啟動 Flask 伺服器
    # H-2 修復：僅綁定 localhost，避免暴露到外網
    # H-3 修復：debug 模式由環境變數控制，預設關閉
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    print("啟動 Magic Eraser 伺服器...")
    print("請在瀏覽器開啟: http://127.0.0.1:5000")
    if debug_mode:
        print("⚠️  Debug 模式已啟用，請勿在生產環境使用！")
    app.run(host='127.0.0.1', port=5000, debug=debug_mode)
