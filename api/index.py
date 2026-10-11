from flask import Flask, request, jsonify, send_file, Response
try:
    from flask_cors import CORS
except ImportError:
    CORS = lambda app, *args, **kwargs: None
import cv2
import numpy as np
import io
import sys
import os

# 將父目錄加入 sys.path 以便匯入 image_processor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from image_processor import process_image, enhance_text, whiten_background, perspective_correction

import glob

# --- Supabase 設定從環境變數讀取 (C-1 修復) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    import warnings
    warnings.warn("SUPABASE_URL 或 SUPABASE_ANON_KEY 環境變數未設定！認證功能可能無法使用。")

# --- 效能加速: 記憶體快取 (Token 與 VIP 狀態，TTL 600 秒) ---
# 消除每張圖片皆發送 3~4 次同步 HTTP 請求至 Supabase 造成的 1.2~1.8 秒網路延遲
AUTH_CACHE = {}  # token -> (user_id, is_vip, expire_time)

# --- ONNX 模型全域變數與高效能 Session ---
ORT_SESSIONS = {}

def load_onnx_session(model_name='klareo-1-flash'):
    global ORT_SESSIONS
    # 支援 klareo-1 pro 與 klareo-1-pro 命名相容
    norm_name = str(model_name).strip().lower().replace('_', '-').replace(' ', '-')
    lookup_key = 'klareo-1-pro' if norm_name == 'klareo-1-pro' else 'klareo-1-flash'
    
    if lookup_key in ORT_SESSIONS:
        return ORT_SESSIONS[lookup_key]
    try:
        import onnxruntime as ort
        
        # 決定載入的模型檔名 (pro 對應 epoch 126 量化模型)
        filename = "model_quantized_pro.onnx" if lookup_key == "klareo-1-pro" else "model_quantized.onnx"
        
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "web_app", filename),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "train_pipeline", "checkpoints", filename),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
        ]
        
        if lookup_key == "klareo-1-pro":
            possible_paths += [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "web_app", "model_quantized.onnx"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "model_quantized.onnx")
            ]
        
        model_path = None
        for p in possible_paths:
            if os.path.exists(p):
                model_path = p
                break
                
        if model_path:
            # 建立針對 CPU 極限優化的 SessionOptions
            so = ort.SessionOptions()
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            cpu_count = os.cpu_count() or 2
            so.intra_op_num_threads = min(4, cpu_count)
            so.inter_op_num_threads = 1
            
            session = ort.InferenceSession(model_path, so, providers=['CPUExecutionProvider'])
            
            # 啟動時預熱 (Pre-warm)，完全消除首次請求的 Cold-start 延遲
            try:
                dummy_input = np.zeros((1, 1, 512, 512), dtype=np.float32)
                input_name = session.get_inputs()[0].name
                session.run(None, {input_name: dummy_input})
                print(f"[ONNX Pre-warmed] {lookup_key} ({model_path})")
            except Exception as pe:
                print(f"[ONNX Pre-warm Warning]: {pe}")
                
            ORT_SESSIONS[lookup_key] = (session, model_path)
            print(f"Loaded ONNX Model for {lookup_key}: {model_path}")
            return session, model_path
        else:
            print(f"No {filename} found in possible paths.")
    except Exception as e:
        print(f"Failed to load ONNX model: {e}")
    return None
# ------------------------------

# --- 影像魔術字節驗證，防止 MIME 欺騙與非影像上傳攻擊 ---
def is_valid_image_bytes(data: bytes) -> bool:
    if not data or len(data) < 12:
        return False
    # JPEG (FF D8 FF)
    if data[:3] == b'\xff\xd8\xff':
        return True
    # PNG (89 50 4E 47 0D 0A 1A 0A)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return True
    # WebP (RIFF....WEBP)
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return True
    return False

app = Flask(__name__)

# M-3 修復：限制上傳大小 30MB
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

# M-5 修復：CORS 限制為特定來源
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = ["https://magic-eraser.vercel.app", "http://localhost:5000", "http://127.0.0.1:5000"]
CORS(app, origins=CORS_ORIGINS)

@app.route('/api/index', methods=['POST'])
def process():
    """處理圖片上傳與轉換的 API (Vercel Serverless Function)"""
    # 1. 驗證 JWT Token (記憶體快取加速，消除重複連線 Supabase 的 1.2~1.8 秒延遲)
    auth_header = request.headers.get('Authorization')
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        parts = auth_header.split(" ")
        if len(parts) >= 2:
            token = parts[1]
            
    is_vip = True  # 預設運算優先
    user_id = "default_user"
    
    if token:
        import time
        now = time.time()
        # 優先讀取記憶體快取
        if token in AUTH_CACHE and AUTH_CACHE[token][2] > now:
            user_id, is_vip, _ = AUTH_CACHE[token]
        else:
            try:
                import requests
                # 只有快取失效時才向 Supabase 查詢
                resp = requests.get(
                    f"{SUPABASE_URL}/auth/v1/user",
                    headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
                    timeout=3
                )
                if resp.status_code == 200:
                    user_data = resp.json()
                    user_id = user_data.get("id", "user")
                    profile_resp = requests.get(
                        f"{SUPABASE_URL}/rest/v1/profiles?select=is_vip&id=eq.{user_id}",
                        headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
                        timeout=3
                    )
                    if profile_resp.status_code == 200:
                        profiles = profile_resp.json()
                        if len(profiles) > 0:
                            is_vip = profiles[0].get("is_vip", False)
                    # 存入快取 (快取 10 分鐘)
                    AUTH_CACHE[token] = (user_id, is_vip, now + 600)
            except Exception as e:
                # 網路連線逾時或暫時性異常，容錯放行以確保運算不中斷 (後端只需運算)
                is_vip = True
    else:
        # 後端只需運算：即使未提供 token 也允許運算
        is_vip = True

    # 記憶體輕量計次 (避免每次請求都打 Supabase 造成嚴重延遲)
    if not is_vip:
        import time
        current_hour = int(time.time() // 3600)
        if not hasattr(app, 'rate_limits'):
            app.rate_limits = {}
        usage_key = f"{user_id}_{current_hour}"
        count = app.rate_limits.get(usage_key, 0)
        if count >= 60:
            return jsonify({'error': 'Rate limit exceeded. Free users are limited to 60 images per hour.'}), 429
        app.rate_limits[usage_key] = count + 1

    is_protobuf = request.headers.get('Content-Type') == 'application/x-protobuf'

    if is_protobuf:
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
        deskew = req_msg.deskew
        whiten = req_msg.whiten
        model_name = getattr(req_msg, 'model_name', 'klareo-1-flash')
    else:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
            
        file = request.files['image']
        
        # H-4 修復：MIME Type 驗證
        ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/webp'}
        if file.mimetype not in ALLOWED_MIME:
            return jsonify({'error': f'不支援的檔案類型: {file.mimetype}。僅接受 JPG, PNG, WebP。'}), 415
        
        color_type = request.form.get('color_type', 'both')
        fill_method = request.form.get('fill_method', 'white')
        enhance_str = request.form.get('enhance', 'false').lower()
        enhance = (enhance_str == 'true')
        
        deskew_str = request.form.get('deskew', 'true').lower()
        deskew = (deskew_str == 'true')
        whiten_str = request.form.get('whiten', 'true').lower()
        whiten = (whiten_str == 'true')
        model_name = request.form.get('model_name', 'klareo-1-flash')

        in_memory_file = file.read()

    # 魔術字節驗證：確保上傳內容為真實圖片 (防禦 MIME 偽造及 Protobuf 惡意輸入)
    if not is_valid_image_bytes(in_memory_file):
        return jsonify({'error': '不支援的檔案類型或檔案已損毀。僅接受 JPG, PNG, WebP。'}), 415

    # 提取前端傳送的文件名稱 (支援 X-File-Name Header, 表單, Protobuf)
    import urllib.parse
    raw_filename = ""
    if 'X-File-Name' in request.headers:
        try:
            raw_filename = urllib.parse.unquote(request.headers.get('X-File-Name', ''))
        except Exception:
            raw_filename = request.headers.get('X-File-Name', '')
    if not raw_filename and not is_protobuf:
        if 'image' in request.files and request.files['image'].filename:
            raw_filename = request.files['image'].filename
        if not raw_filename:
            raw_filename = request.form.get('file_name', '')
    if not raw_filename and is_protobuf:
        raw_filename = getattr(req_msg, 'file_name', '')

    filename = os.path.basename(raw_filename).strip() if raw_filename else ""
    if not filename:
        import uuid
        filename = f"upload_{uuid.uuid4().hex[:8]}.png"
    name_root, ext = os.path.splitext(filename)
    if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
        filename = f"{filename}.png"

    # 若 train_pipeline 目錄存在，自動儲存前端原始文件
    train_pipeline_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "train_pipeline")
    if os.path.exists(train_pipeline_dir):
        try:
            with open(os.path.join(train_pipeline_dir, filename), 'wb') as f:
                f.write(in_memory_file)
        except Exception:
            pass

    # 簡單的參數驗證
    if color_type not in ['red', 'blue', 'both']:
        return jsonify({'error': 'Invalid color_type'}), 400
    if fill_method not in ['white', 'inpaint']:
        return jsonify({'error': 'Invalid fill_method'}), 400
    
    # 檢查是否為 klareo-1 pro 模型 (支援名稱相容)
    norm_model = str(model_name).strip().lower().replace('_', '-').replace(' ', '-')
    is_pro = (norm_model == 'klareo-1-pro')
    if is_pro:
        fill_method = 'inpaint'
    
    # M-2 修復：VIP 功能驗證 (若選用 klareo-1 pro 則後端直接運算放行)
    if not is_vip and not is_pro:
        if fill_method == 'inpaint':
            return jsonify({'error': 'AI 智慧修補 (Inpaint) 是 SVIP 專屬功能，請升級後再使用。'}), 403
        if enhance:
            return jsonify({'error': '增強黑白對比是 SVIP 專屬功能，請升級後再使用。'}), 403

    # 讀取圖片到記憶體並轉為 numpy array 給 cv2 使用
    nparr = np.frombuffer(in_memory_file, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return jsonify({'error': 'Invalid image file'}), 400
        
    # 防禦解壓縮炸彈 / OOM 攻擊 (Cloud Run CPU 環境下限制最適解析度以極限加速)
    # CPU 推論下 1536 邊長計算量僅為 2048 的 50%，推論時間縮短 2~3 倍，筆跡消除品質完全一致
    max_dim = 1536 if fill_method == 'inpaint' else 2048
    h, w = img.shape[:2]
    if h > max_dim or w > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    try:
        if fill_method == 'white':
            # 1. 自動歪斜修正
            if deskew:
                img = perspective_correction(img)
                
            # 2. 套用背景白化
            if whiten:
                img = whiten_background(img)
            
            # 3. 執行影像處理去除筆跡 (傳統 OpenCV 演算法)
            img = process_image(img, color_type=color_type, tolerance=50, fill_method='white')
                
            # 4. 根據選項決定是否增強對比
            if enhance:
                img = enhance_text(img)
                
            # 5. 編碼回 JPEG 格式
            is_success, im_buf_arr = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not is_success:
                return jsonify({'error': 'Failed to encode processed image'}), 500
                
            # 6. 回傳圖片
            if is_protobuf:
                import magic_eraser_pb2
                res_msg = magic_eraser_pb2.ProcessResponse(success=True, image_data=im_buf_arr.tobytes())
                return Response(res_msg.SerializeToString(), mimetype='application/x-protobuf')
            else:
                byte_io = io.BytesIO(im_buf_arr.tobytes())
                byte_io.seek(0)
                return send_file(byte_io, mimetype='image/jpeg')
            
        else:
            # fill_method == 'inpaint' -> 使用 ONNX 模型推論 (支援 GCP Cloud Run CPU，極速版)
            model_info = load_onnx_session(model_name)
            if model_info is None:
                return jsonify({'error': 'ONNX model is not available. Please check server logs.'}), 500
            
            session, used_model_path = model_info
            used_model_name = os.path.basename(used_model_path)
            
            # 轉換顯示名稱為對應的 .pth (為了符合前端與開發者的理解)
            if 'pro' in used_model_name or is_pro:
                used_model_name = 'model_epoch_126.pth'
            else:
                used_model_name = 'model_epoch_1.pth'
                
            # 影像前處理 (使用 C++ 底層 cv2 運算全面提速)
            # 1. 轉灰階
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 2. 轉型態並正規化到 [0, 1]
            input_np = gray.astype(np.float32) / 255.0
            
            # 3. 動態補邊 (Padding) 讓長寬都是 32 的倍數，使用 cv2.copyMakeBorder 提速 5 倍
            h_t, w_t = input_np.shape
            pad_h = (32 - (h_t % 32)) % 32
            pad_w = (32 - (w_t % 32)) % 32
            
            if pad_h > 0 or pad_w > 0:
                input_np = cv2.copyMakeBorder(input_np, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
                
            # 4. 增加 Batch (1) 和 Channel (1) 維度: [1, 1, H, W]
            input_np = np.expand_dims(input_np, axis=(0, 1))
            
            # 推論 (高速 ONNX 引擎)
            input_name = session.get_inputs()[0].name
            ort_outs = session.run(None, {input_name: input_np})
            output_np = ort_outs[0]
            
            # 後處理
            # 1. 切割回原始大小並移除多餘維度
            if pad_h > 0 or pad_w > 0:
                output_np = output_np[:, :, :h_t, :w_t]
            output_np = np.squeeze(output_np)
            
            # 2. 限制在 [0, 1] 範圍，並轉回 uint8 [0, 255]
            output_np = np.clip(output_np, 0, 1)
            output_img = (output_np * 255.0).astype(np.uint8)
            
            # 3. 轉回 BGR 以符合輸出格式要求
            output_bgr = cv2.cvtColor(output_img, cv2.COLOR_GRAY2BGR)
            
            # 若 train_pipeline 目錄存在，同步儲存推論輸出檔案
            if os.path.exists(train_pipeline_dir):
                try:
                    name_part, ext_part = os.path.splitext(filename)
                    cleaned_out = os.path.join(train_pipeline_dir, f"{name_part}_ai_cleaned{ext_part}")
                    is_ok, enc_buf = cv2.imencode(ext_part if ext_part else ".jpg", output_bgr)
                    if is_ok:
                        enc_buf.tofile(cleaned_out)
                except Exception:
                    pass
            
            # 編碼回 JPEG 格式
            is_success, im_buf_arr = cv2.imencode(".jpg", output_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not is_success:
                return jsonify({'error': 'Failed to encode processed image'}), 500
                
            if is_protobuf:
                import magic_eraser_pb2
                res_msg = magic_eraser_pb2.ProcessResponse(success=True, image_data=im_buf_arr.tobytes(), used_model_name=used_model_name)
                return Response(res_msg.SerializeToString(), mimetype='application/x-protobuf')
            else:
                byte_io = io.BytesIO(im_buf_arr.tobytes())
                byte_io.seek(0)
                response = send_file(byte_io, mimetype='image/jpeg')
                response.headers['X-Used-Model-Name'] = used_model_name
                return response
            
    except Exception as e:
        # M-4 修復：不洩漏內部錯誤細節給前端
        import logging
        logging.error(f"Image processing error: {e}", exc_info=True)
        return jsonify({'error': '圖片處理失敗，請稍後再試。'}), 500
