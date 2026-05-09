import cv2
import numpy as np

def whiten_background_new(image):
    if image is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h_orig, w_orig = gray.shape
    scale = 0.2
    gray_small = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
    kernel = np.ones((11, 11), np.uint8)
    bg_gray_small = cv2.dilate(gray_small, kernel)
    bg_gray = cv2.resize(bg_gray_small, (w_orig, h_orig))
    bg_gray = np.maximum(bg_gray, 1)
    
    image_float = image.astype(np.float32)
    bg_gray_float = bg_gray.astype(np.float32)
    bg_gray_float = np.expand_dims(bg_gray_float, axis=-1)
    
    result = np.clip((image_float / bg_gray_float) * 255.0, 0, 255).astype(np.uint8)
    return result

img = np.full((500, 500, 3), 180, dtype=np.uint8)
cv2.putText(img, 'Testing Text', (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 5)
cv2.putText(img, 'Blue Text', (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 5)

result = whiten_background_new(img)
cv2.imwrite('test_output2.png', result)
print("Done. Saved test_output2.png")
