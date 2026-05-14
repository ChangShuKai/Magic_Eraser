import cv2
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# 全域模型快取（延遲載入）
# ─────────────────────────────────────────────────────────────────────────────
_lama_model = None
_easyocr_reader = None


def get_lama_model():
    """取得或初始化 LaMa AI 修補模型（單例模式）"""
    global _lama_model
    if _lama_model is None:
        try:
            from simple_lama_inpainting import SimpleLama
            print("載入 LaMa AI 修補模型中（首次需約 30 秒）...")
            _lama_model = SimpleLama()
            print("✅ LaMa 模型載入完成。")
        except ImportError:
            print("❌ 錯誤：尚未安裝 simple-lama-inpainting。請執行 pip install simple-lama-inpainting")
            return None
        except Exception as e:
            print(f"❌ LaMa 模型載入失敗: {e}")
            return None
    return _lama_model


def get_easyocr_reader():
    """取得或初始化 EasyOCR 文字偵測器（GPU 加速）"""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            import torch
            use_gpu = torch.cuda.is_available()
            if use_gpu:
                print("🚀 偵測到 CUDA GPU，EasyOCR 將使用 RTX 3060 加速！")
            else:
                print("⚠️  未偵測到 CUDA GPU，EasyOCR 將使用 CPU（速度較慢）。")
            print("載入 EasyOCR 文字偵測模型中（首次需下載約 200MB）...")
            # 支援繁體中文與英文
            _easyocr_reader = easyocr.Reader(['ch_tra', 'en'], gpu=use_gpu)
            print("✅ EasyOCR 模型載入完成。")
        except ImportError:
            print("❌ 錯誤：尚未安裝 easyocr。請執行 pip install easyocr")
            return None
        except Exception as e:
            print(f"❌ EasyOCR 模型載入失敗: {e}")
            return None
    return _easyocr_reader


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 + 2：文字偵測 + 手寫分類
# ─────────────────────────────────────────────────────────────────────────────

def _is_handwritten_region(crop_bgr, hsv_crop, bbox_h):
    """
    分析裁切區域的視覺特徵，判斷是否為手寫字。
    
    策略（不需要大型神經網路）：
    1. 顏色：若飽和度高 (S > 25)，為彩色筆 → 一定是手寫
    2. 筆劃均勻度：手寫字筆劃粗細差異大，印刷字高度均勻
    3. 輪廓複雜度：手寫字邊緣不規則，印刷字邊緣乾淨
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return False

    # --- 特徵 1：顏色偵測（彩色筆跡）---
    s_channel = hsv_crop[:, :, 1]
    # 如果超過 5% 的像素飽和度 > 30，判定為彩色手寫
    color_ratio = np.sum(s_channel > 30) / (s_channel.size + 1e-6)
    if color_ratio > 0.05:
        return True

    # --- 特徵 2：筆劃均勻度分析 ---
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    # 二值化
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 計算每一行的墨水量（水平剖面），手寫字行間差異大
    row_sums = np.sum(binary > 0, axis=1).astype(float)
    if len(row_sums) > 3:
        row_std = np.std(row_sums)
        row_mean = np.mean(row_sums)
        # 均勻度比值：印刷字比值低（均勻），手寫字比值高（不均勻）
        if row_mean > 0:
            uniformity_ratio = row_std / (row_mean + 1e-6)
            if uniformity_ratio > 0.8:  # 高度不均勻 → 手寫
                return True

    # --- 特徵 3：輪廓複雜度 ---
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # 計算最大輪廓的複雜度 (周長^2 / 面積)，手寫字通常較高
        complexities = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            if area > 5:
                complexity = (perimeter ** 2) / (area + 1e-6)
                complexities.append(complexity)
        
        if complexities:
            avg_complexity = np.mean(complexities)
            # 手寫字（尤其草書）複雜度通常遠高於 50
            if avg_complexity > 60:
                return True

    return False


def detect_handwriting_mask(image):
    """
    Stage 1 + 2：使用 EasyOCR 偵測所有文字，
    再用啟發式特徵判別哪些是手寫，生成手寫遮罩。
    
    :param image: OpenCV BGR 圖片
    :return: 手寫遮罩 (uint8, 0=保留, 255=手寫/移除)
    """
    if image is None:
        return None

    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    reader = get_easyocr_reader()
    if reader is None:
        print("EasyOCR 不可用，降級至顏色模式。")
        return None

    # EasyOCR 偵測（paragraph=False 取得更精細的區域框）
    results = reader.readtext(image, paragraph=False, detail=1)
    
    for (bbox_pts, text, conf) in results:
        if conf < 0.1:  # 過濾極低信心的結果
            continue

        # 從 EasyOCR 的多邊形框取得矩形邊界
        pts = np.array(bbox_pts, dtype=np.int32)
        x, y, bw, bh = cv2.boundingRect(pts)
        
        # 邊界裁剪，避免越界
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w, x + bw)
        y2 = min(h, y + bh)

        if x2 <= x1 or y2 <= y1:
            continue

        # 裁出這個文字區域
        crop = image[y1:y2, x1:x2]
        hsv_crop = hsv[y1:y2, x1:x2]

        # Stage 2：判斷是否為手寫
        if _is_handwritten_region(crop, hsv_crop, bh):
            # 將手寫區域加入遮罩（稍微膨脹以包含完整筆跡）
            pad = max(3, int(bh * 0.1))
            mx1, my1 = max(0, x1 - pad), max(0, y1 - pad)
            mx2, my2 = min(w, x2 + pad), min(h, y2 + pad)
            mask[my1:my2, mx1:mx2] = 255

    # 連通性後處理：合併鄰近的手寫遮罩塊
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    mask = cv2.erode(mask, kernel, iterations=1)

    return mask


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3：LaMa AI 修補
# ─────────────────────────────────────────────────────────────────────────────

def _inpaint_with_lama(image, mask):
    """使用 LaMa AI 模型（RTX 3060 GPU 加速）進行無痕修補"""
    lama = get_lama_model()
    if lama is None:
        # 降級：使用 OpenCV inpainting
        print("⚠️  LaMa 不可用，使用 OpenCV 降級修補。")
        return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)

    try:
        from PIL import Image
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        pil_mask = Image.fromarray(mask)

        inpainted_pil = lama(pil_img, pil_mask)
        inpainted_np = np.array(inpainted_pil)
        return cv2.cvtColor(inpainted_np, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"❌ LaMa 修補失敗: {e}，降級使用 OpenCV。")
        return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)


# ─────────────────────────────────────────────────────────────────────────────
# 主要公開函數
# ─────────────────────────────────────────────────────────────────────────────

def process_image(image, color_type='red', tolerance=50, fill_method='white'):
    """
    去除圖片中的手寫筆記。
    
    :param image: OpenCV BGR image (numpy array)
    :param color_type: 'red', 'blue', 'both', 或 'ai_all'（AI 全模式，包含黑字）
    :param tolerance: 容差值（保留相容性，目前未使用）
    :param fill_method: 'white' (填白), 'inpaint' (OpenCV修補), 'ai' (LaMa AI修補)
    :return: 處理後的 OpenCV BGR image
    """
    if image is None:
        return None

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # ── AI 全模式：偵測所有手寫字（含黑色）──
    if color_type == 'ai_all':
        mask = detect_handwriting_mask(image)
        if mask is None:
            # EasyOCR 不可用，降級為顏色模式
            print("⚠️  AI 全模式降級為顏色模式（紅+藍）")
            color_type = 'both'
            # 繼續到下面的顏色模式流程
        else:
            return _apply_fill(image, mask, fill_method)

    # ── 顏色模式：精準去除彩色筆跡（快速，不含黑色）──
    # 飽和度下限提高到 65，真正的彩色筆跡 S 通常 > 80，印刷字 S < 20
    s_lower = 65
    v_lower = 40

    lower_red1 = np.array([0, s_lower, v_lower])
    upper_red1 = np.array([10, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([170, s_lower, v_lower])
    upper_red2 = np.array([180, 255, 255])
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = mask_red1 + mask_red2

    lower_blue = np.array([90, s_lower, v_lower])
    upper_blue = np.array([130, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    if color_type == 'red':
        mask = mask_red
    elif color_type == 'blue':
        mask = mask_blue
    else:  # 'both'
        mask = cv2.bitwise_or(mask_red, mask_blue)

    # ── 保護黑色印刷字（大幅膨脹以建立安全緩衝區）──
    _, s, v = cv2.split(hsv)
    # 印刷黑字：低飽和(S<40) 且 低亮度(V<180)
    protect_core = cv2.bitwise_and(
        cv2.compare(s, 40, cv2.CMP_LT),
        cv2.compare(v, 180, cv2.CMP_LT)
    )
    # 膨脹 4 次，讓黑字周圍有足夠的保護緩衝區
    protect_kernel = np.ones((5, 5), np.uint8)
    protect_mask = cv2.dilate(protect_core, protect_kernel, iterations=4)

    # 彩色遮罩只膨脹 1 次（夠填補筆跡間隙，又不會大量吃字）
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)

    # 從彩色遮罩中排除印刷字保護區
    mask = cv2.bitwise_and(mask, cv2.bitwise_not(protect_mask))

    return _apply_fill(image, mask, fill_method)


def _apply_fill(image, mask, fill_method):
    """根據選擇的填補模式，將遮罩區域填補。"""
    result = image.copy()

    if fill_method == 'white':
        result[mask > 0] = (255, 255, 255)
    elif fill_method == 'ai':
        result = _inpaint_with_lama(result, mask)
    else:  # 'inpaint'（OpenCV 傳統修補）
        result = cv2.inpaint(result, mask, 3, cv2.INPAINT_TELEA)

    return result


def whiten_background(image):
    """
    更專業的背景去污與光照補償。
    使用大尺寸的高斯模糊提取背景光照圖，然後進行動態範圍增益。
    """
    if image is None:
        return None

    # 1. 估計背景光照 (使用大核膨脹 + 高斯模糊)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 縮小處理以提升速度
    h, w = gray.shape
    scale = 0.25
    small = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
    
    # 提取亮部 (背景)
    kernel_size = max(1, int(31 * scale))
    if kernel_size % 2 == 0: kernel_size += 1
    
    bg_small = cv2.dilate(small, np.ones((kernel_size, kernel_size), np.uint8))
    bg_small = cv2.GaussianBlur(bg_small, (kernel_size, kernel_size), 0)
    
    # 放大回原圖
    bg = cv2.resize(bg_small, (w, h))
    bg = np.maximum(bg, 1) # 避免除以 0

    # 2. 除法正規化 (Lighting Compensation)
    image_f = image.astype(np.float32)
    bg_f = bg.astype(np.float32)[:, :, np.newaxis]
    
    result = (image_f / bg_f) * 255.0
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    # 3. 微調對比度與亮度，讓白色更白，黑色更黑
    # 使用線性變換：y = ax + b
    # alpha = 1.1, beta = -10
    result = cv2.convertScaleAbs(result, alpha=1.1, beta=-10)
    
    return result


def enhance_text(image):
    """
    增強文字清晰度，使用基於內容的拉伸而非簡單的二值化。
    """
    if image is None:
        return None
    
    # 轉為灰階
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 使用局部對比增強 (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    
    # 稍微銳化
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced_gray, -1, kernel)
    
    # 轉回 BGR 以保持介面一致性
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
