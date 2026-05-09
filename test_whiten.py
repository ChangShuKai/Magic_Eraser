import cv2
import numpy as np
from image_processor import whiten_background

# 建立一個測試用的全灰圖片
img = np.full((1000, 1000, 3), 128, dtype=np.uint8)

print("Starting whiten_background...")
try:
    result = whiten_background(img)
    print("Done! Result shape:", result.shape)
except Exception as e:
    print("Crash!", e)
