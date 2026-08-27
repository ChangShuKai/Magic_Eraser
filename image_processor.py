import cv2
import numpy as np

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def perspective_correction(image):
    """
    自動歪斜修正 (Perspective Correction)。
    嘗試尋找圖片中的最大四邊形輪廓（例如紙張邊緣），並將其拉正。
    如果找不到明顯的四邊形，則回傳原圖。
    """
    if image is None:
        return None
    
    # 縮小圖片以加快邊緣檢測
    ratio = image.shape[0] / 500.0
    orig = image.copy()
    if ratio > 1:
        img_small = cv2.resize(image, (int(image.shape[1] / ratio), 500))
    else:
        img_small = image.copy()
        ratio = 1.0

    gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 75, 200)

    # 尋找輪廓
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    
    # 取前五個最大的輪廓
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    doc_cnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        # 如果輪廓有四個點，我們就認為它是一張紙
        if len(approx) == 4:
            doc_cnt = approx
            break

    # 若有找到四邊形且面積夠大，才進行轉換
    if doc_cnt is not None and cv2.contourArea(doc_cnt) > (img_small.shape[0]*img_small.shape[1]*0.1):
        # 轉換回原圖座標
        doc_cnt = doc_cnt.reshape(4, 2) * ratio
        rect = order_points(doc_cnt)
        (tl, tr, br, bl) = rect

        # 計算新圖片的寬度
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        # 計算新圖片的高度
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        # 變換矩陣
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        return warped
    
    return image
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
    
    # 為了能徹底清除淡色筆跡與邊緣暈染，將飽和度與明度閾值進一步降低
    s_lower = 15
    v_lower = 15
    
    # 紅色與粉紅色的 HSV 範圍 (OpenCV的 H 範圍是 0-179)
    lower_red1 = np.array([0, s_lower, v_lower])
    upper_red1 = np.array([20, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([140, s_lower, v_lower])
    upper_red2 = np.array([180, 255, 255])
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    mask_red = mask_red1 + mask_red2

    # 藍色與淺藍色的 HSV 範圍
    lower_blue = np.array([80, s_lower, v_lower])
    upper_blue = np.array([140, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    if color_type == 'red':
        mask = mask_red
    elif color_type == 'blue':
        mask = mask_blue
    elif color_type == 'both':
        # "除了黑色都去除"：擷取所有色相 (Hue 0~179)
        # 只要飽和度(S)與明度(V)高於閾值，即視為彩色筆跡
        lower_all = np.array([0, s_lower, v_lower])
        upper_all = np.array([179, 255, 255])
        mask = cv2.inRange(hsv, lower_all, upper_all)
    else:
        return image.copy()

    # 建立保護遮罩：保護黑色/深灰色印刷字，避免掃描邊緣色差被當成筆跡
    # 黑字核心特徵：飽和度低 (S < 50) 且 明度非常低 (V < 150)
    # 我們只保護「真正的黑字核心」，這樣就不會誤保護到紅/藍筆跡的淡淡邊緣 (V通常>150)
    _, s, v = cv2.split(hsv)
    protect_core = cv2.bitwise_and(
        cv2.compare(s, 50, cv2.CMP_LT),
        cv2.compare(v, 150, cv2.CMP_LT)
    )
    # 將保護遮罩稍微膨脹 (3x3)，確保黑字邊緣被保護，但不過度影響附近筆跡
    protect_kernel = np.ones((3, 3), np.uint8)
    protect_mask = cv2.dilate(protect_core, protect_kernel, iterations=1)

    # 使用形態學操作 (膨脹) 來確保筆跡淡淡的邊緣也被完全包含在要刪除的遮罩內
    kernel_size = 5
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    # 從要去除的遮罩中，排除受保護的黑字區域
    mask = cv2.bitwise_and(mask, cv2.bitwise_not(protect_mask))

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
