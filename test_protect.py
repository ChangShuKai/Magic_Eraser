import cv2
import numpy as np

def process_test(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # 模擬黑字與邊緣色差
    s_lower = 30
    v_lower = 30
    
    lower_blue = np.array([90, s_lower, v_lower])
    upper_blue = np.array([130, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    
    mask = mask_blue
    
    # 建立保護遮罩
    protect_mask = cv2.bitwise_and(
        cv2.compare(s, 60, cv2.CMP_LT),
        cv2.compare(v, 200, cv2.CMP_LT)
    )
    protect_kernel = np.ones((3, 3), np.uint8)
    protect_mask = cv2.dilate(protect_mask, protect_kernel, iterations=1)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    mask = cv2.bitwise_and(mask, cv2.bitwise_not(protect_mask))
    
    result = image.copy()
    result[mask > 0] = (255, 255, 255)
    return result

# 產生一個測試圖片: 白底, 黑字(帶一點藍色邊緣), 純藍色筆跡
img = np.full((300, 400, 3), 255, dtype=np.uint8)
# 畫純藍色筆跡
cv2.putText(img, 'Handwriting', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
# 畫黑字
cv2.putText(img, 'Printed Text', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
# 模擬黑字的藍色邊緣色差
cv2.putText(img, 'Printed Text', (52, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (150, 50, 50), 1) # BGR=(150,50,50) 是深藍/紫色

res = process_test(img)
cv2.imwrite('test_protect.png', res)
print("Saved test_protect.png")
