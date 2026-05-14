import cv2
import numpy as np

def process_image(image, color_type='both', tolerance=50, fill_method='white'):
    """
    去除圖片中的手寫筆記（傳統模式）。
    
    :param image: OpenCV BGR image (numpy array)
    :param color_type: 'red', 'blue', 'both'
    :param tolerance: 容差值（保留相容性）
    :param fill_method: 'white' (填白), 'inpaint' (OpenCV修補)
    :return: 處理後的 OpenCV BGR image
    """
    if image is None:
        return None

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # ── 顏色模式：精準去除彩色筆跡（快速，不含黑色）──
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

    # ── 保護黑色印刷字（建立安全緩衝區）──
    _, s, v = cv2.split(hsv)
    protect_core = cv2.bitwise_and(
        cv2.compare(s, 40, cv2.CMP_LT),
        cv2.compare(v, 180, cv2.CMP_LT)
    )
    protect_kernel = np.ones((5, 5), np.uint8)
    protect_mask = cv2.dilate(protect_core, protect_kernel, iterations=4)

    # 彩色遮罩稍微膨脹
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
    else:  # 'inpaint'（OpenCV 傳統修補）
        result = cv2.inpaint(result, mask, 3, cv2.INPAINT_TELEA)
    return result


def whiten_background(image):
    """
    更專業的背景去污與光照補償。
    """
    if image is None:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = 0.25
    small = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
    
    kernel_size = max(1, int(31 * scale))
    if kernel_size % 2 == 0: kernel_size += 1
    
    bg_small = cv2.dilate(small, np.ones((kernel_size, kernel_size), np.uint8))
    bg_small = cv2.GaussianBlur(bg_small, (kernel_size, kernel_size), 0)
    
    bg = cv2.resize(bg_small, (w, h))
    bg = np.maximum(bg, 1)

    image_f = image.astype(np.float32)
    bg_f = bg.astype(np.float32)[:, :, np.newaxis]
    
    result = (image_f / bg_f) * 255.0
    result = np.clip(result, 0, 255).astype(np.uint8)
    result = cv2.convertScaleAbs(result, alpha=1.1, beta=-10)
    return result


def enhance_text(image):
    """
    增強文字清晰度。
    """
    if image is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced_gray, -1, kernel)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
