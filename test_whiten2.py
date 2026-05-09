import cv2
import numpy as np
from image_processor import whiten_background

# 建立一個有漸層灰底和黑字的圖片
img = np.full((500, 500, 3), 180, dtype=np.uint8) # 灰底
cv2.putText(img, 'Testing Text', (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 5)
cv2.putText(img, 'Blue Text', (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 5) # BGR: blue is (255,0,0)

cv2.imwrite('test_input.png', img)

result = whiten_background(img)
cv2.imwrite('test_output.png', result)
print("Done. Saved test_input.png and test_output.png")
