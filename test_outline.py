import cv2
import numpy as np

def process_test(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    s_lower = 30
    v_lower = 30
    
    lower_red1 = np.array([0, s_lower, v_lower])
    upper_red1 = np.array([10, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([170, s_lower, v_lower])
    upper_red2 = np.array([180, 255, 255])
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask_red1 + mask_red2
    
    # 建立保護遮罩
    # 核心黑字：明度極低且飽和度低
    protect_core = cv2.bitwise_and(
        cv2.compare(s, 50, cv2.CMP_LT),
        cv2.compare(v, 150, cv2.CMP_LT)
    )
    # 稍微膨脹保護核心，涵蓋邊緣色差
    protect_kernel = np.ones((5, 5), np.uint8)
    protect_mask = cv2.dilate(protect_core, protect_kernel, iterations=1)
    
    # 膨脹紅藍遮罩
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    # 排除保護區
    mask = cv2.bitwise_and(mask, cv2.bitwise_not(protect_mask))
    
    result = image.copy()
    # 模擬 inpaint 的白色填補
    result[mask > 0] = (255, 255, 255)
    
    # 儲存除錯圖片
    cv2.imwrite('debug_protect_core.png', protect_core)
    cv2.imwrite('debug_protect_mask.png', protect_mask)
    cv2.imwrite('debug_red_mask.png', mask)
    
    return result

# 生成模擬圖
img = np.full((300, 400, 3), 255, dtype=np.uint8)
# 黑字
cv2.putText(img, 'Printed', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (50, 50, 50), 4) # 深灰色代表掃描黑字
cv2.putText(img, 'Printed', (52, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (120, 120, 200), 1) # 紅色邊緣色差
# 紅筆跡 (帶有淡化邊緣)
cv2.putText(img, 'Handwriting', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4) # 純紅中心
cv2.putText(img, 'Handwriting', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (180, 180, 255), 8) # 粉紅邊緣(代表墨水暈開)

res = process_test(img)
cv2.imwrite('test_outline.png', res)
print("Done")
