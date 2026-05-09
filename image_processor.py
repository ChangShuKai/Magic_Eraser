import cv2
import numpy as np

def process_image(image, color_type='red', tolerance=50, fill_method='white'):
    """
    去除圖片中指定顏色的手寫筆記
    :param image: OpenCV BGR image (numpy array)
    :param color_type: 'red', 'blue', 或 'both'
    :param tolerance: 容差值 (0-100)，影響遮罩膨脹程度和範圍
    :param fill_method: 'white' (直接填白) 或 'inpaint' (周圍修補)
    :return: 處理後的 OpenCV BGR image
    """
    if image is None:
        return None

    # 轉換為 HSV 色彩空間
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 為了避免將掃描的「黑字邊緣色差」誤判為紅/藍筆，飽和度閾值不能太低
    s_lower = 50
    v_lower = 50
    
    # 紅色的 HSV 範圍
    lower_red1 = np.array([0, s_lower, v_lower])
    upper_red1 = np.array([10, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([170, s_lower, v_lower])
    upper_red2 = np.array([180, 255, 255])
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    mask_red = mask_red1 + mask_red2

    # 藍色的 HSV 範圍
    lower_blue = np.array([90, s_lower, v_lower])
    upper_blue = np.array([130, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    if color_type == 'red':
        mask = mask_red
    elif color_type == 'blue':
        mask = mask_blue
    elif color_type == 'both':
        mask = cv2.bitwise_or(mask_red, mask_blue)
    else:
        # 如果不支援該顏色，直接回傳原圖
        return image.copy()

    # 使用形態學操作 (膨脹) 來確保邊緣也被包含在遮罩內
    # 適度的 kernel 避免誤傷正常文字
    kernel_size = 3
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)

    result = image.copy()

    if fill_method == 'white':
        # 直接將遮罩區域塗白
        result[mask > 0] = (255, 255, 255)
    else:
        # 使用 inpainting 修補 (較慢，但對於非純白背景可能較好)
        # 這裡提供作為一個進階選項
        inpaint_radius = 3
        result = cv2.inpaint(result, mask, inpaint_radius, cv2.INPAINT_TELEA)

    return result

def whiten_background(image):
    """
    保留顏色的背景白化處理 (去除灰底和陰影)。
    轉為灰階後使用膨脹操作提取背景，再利用除法正規化讓灰底變白，同時保留墨水與印刷字顏色。
    """
    if image is None:
        return None
        
    # 將圖像轉換為灰階，因為在灰階中，不論藍色或紅色筆跡都比白紙背景「暗」
    # 這樣膨脹(Dilate)操作就能正確吃掉所有字跡，提取出純淨的背景光照
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 為了避免高解析度圖片運算過久導致當機，先將圖片縮小再做膨脹
    h_orig, w_orig = gray.shape
    scale = 0.2 # 縮小到 1/5 提升百倍速度
    gray_small = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
    
    # 使用膨脹(Dilate)來找背景，能有效吃掉深色字跡，留下亮色背景
    kernel = np.ones((11, 11), np.uint8)
    bg_gray_small = cv2.dilate(gray_small, kernel)
    
    # 放大回原圖尺寸
    bg_gray = cv2.resize(bg_gray_small, (w_orig, h_orig))
    
    # 為了安全起見，避免除以 0
    bg_gray = np.maximum(bg_gray, 1)
    
    # 將原始 BGR 三個通道分別除以背景 (灰階)
    # 這樣原本是背景的像素就會變成 255 (純白)，而且能保留顏色比例
    image_float = image.astype(np.float32)
    bg_gray_float = bg_gray.astype(np.float32)
    
    # bg_gray_float 只有單通道，需要變成 (H, W, 1) 以便廣播除法
    bg_gray_float = np.expand_dims(bg_gray_float, axis=-1)
    
    result = np.clip((image_float / bg_gray_float) * 255.0, 0, 255).astype(np.uint8)
    
    return result

def enhance_text(image):
    """
    可選：增強黑白對比，讓考卷看起來更乾淨
    """
    if image is None:
        return None
    # 轉灰階
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 自適應二值化 (可讓背景變白，文字變黑)
    # 這邊僅為示範，實際應用可能會讓圖片太像純掃描檔
    # 如果使用者只是要去除手寫，不一定要套用這個
    enhanced = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 21, 10)
    # 轉回 BGR 以便統一介面顯示
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    return enhanced_bgr
