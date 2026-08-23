import torch
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import os
from model import MobileNetV3UNet

def blend_patches(output_buffer, weight_buffer, patch, x, y, patch_size, overlap):
    """
    使用 Hann Window 進行平滑融合 (Blending) 避免邊界縫隙
    """
    # 建立簡單的線性淡出權重
    for dy in range(patch_size):
        for dx in range(patch_size):
            # 計算距離邊界的權重 (0 到 1)
            wx = min(dx, patch_size - 1 - dx) / (overlap / 2.0)
            wy = min(dy, patch_size - 1 - dy) / (overlap / 2.0)
            weight = min(1.0, min(wx, wy))
            
            idx_y = y + dy
            idx_x = x + dx
            if idx_y < output_buffer.shape[0] and idx_x < output_buffer.shape[1]:
                output_buffer[idx_y, idx_x] += patch[dy, dx] * weight
                weight_buffer[idx_y, idx_x] += weight

def infer_image(image_path, model_path, patch_size=512, overlap=32):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # 載入模型
    model = MobileNetV3UNet().to(device)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"Loaded weights from {model_path}")
    else:
        print(f"Warning: {model_path} not found. Using random weights!")
    
    model.eval()
    
    # 讀取圖片
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Could not read image: {image_path}")
        
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = img_gray.shape
    
    print(f"Processing image {image_path} ({w}x{h})...")
    
    stride = patch_size - overlap
    
    # 建立輸出與權重緩衝區
    output_buffer = np.zeros((h, w), dtype=np.float32)
    weight_buffer = np.zeros((h, w), dtype=np.float32)
    
    transform = transforms.Compose([
        transforms.ToTensor()
    ])
    
    # Sliding Window
    with torch.no_grad():
        for y in range(0, h, stride):
            for x in range(0, w, stride):
                # 處理右下角邊界
                start_y = y
                start_x = x
                if start_y + patch_size > h:
                    start_y = h - patch_size
                if start_x + patch_size > w:
                    start_x = w - patch_size
                    
                # 切割 patch
                patch = img_gray[start_y:start_y+patch_size, start_x:start_x+patch_size]
                
                # 轉換為 tensor
                patch_tensor = transform(patch).unsqueeze(0).to(device) # (1, 1, 512, 512)
                
                # 推論
                out_tensor = model(patch_tensor)
                
                # 轉回 numpy
                out_patch = out_tensor.squeeze().cpu().numpy()
                
                # 融合
                blend_patches(output_buffer, weight_buffer, out_patch, start_x, start_y, patch_size, overlap)
                
    # 處理邊緣權重為 0 的情況
    weight_buffer[weight_buffer == 0] = 1.0
    final_img_float = (output_buffer / weight_buffer) * 255.0
    final_img = np.clip(final_img_float, 0, 255).astype(np.uint8)
    
    # 儲存結果
    name, ext = os.path.splitext(image_path)
    out_path = f"{name}_ai_cleaned{ext}"
    cv2.imwrite(out_path, final_img)
    print(f"Output saved to {out_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI 去手寫推論腳本")
    parser.add_argument("-i", "--image", type=str, required=True, help="要處理的圖片路徑 (例如: test.jpg)")
    parser.add_argument("-m", "--model", type=str, default="checkpoints/model_epoch_1.pth", help="模型權重路徑")
    args = parser.parse_args()
    
    infer_image(args.image, args.model)
