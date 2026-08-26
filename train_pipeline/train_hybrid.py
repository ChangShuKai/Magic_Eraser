import os
import glob
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import torchvision.transforms as transforms
from torch.optim.lr_scheduler import CosineAnnealingLR

# 限制 CPU 執行緒
torch.set_num_threads(2)

from model import MobileNetV3UNet
from loss import CompositeLoss

class HybridDataset(Dataset):
    def __init__(self, target_dir, patch_size=512, length=2000):
        self.patch_size = patch_size
        self.length = length
        self.backgrounds = []
        
        # 讀取真實乾淨考卷當作背景
        target_files = sorted(glob.glob(os.path.join(target_dir, "*.png")) + glob.glob(os.path.join(target_dir, "*.jpg")))
        print("Loading clean backgrounds into memory...")
        for tgt_p in target_files:
            tgt_img = Image.open(tgt_p).convert("L")
            tgt_img.load() # 強制載入記憶體，避免延遲讀取造成的快取暴增
            self.backgrounds.append(tgt_img)
        print(f"Loaded {len(self.backgrounds)} clean backgrounds.")
        
        # 手寫字體
        self.hw_fonts = [f for f in ['assets/fonts/ChenYuluoyan-Thin.ttf', 'assets/fonts/setofont.ttf'] if os.path.exists(f)]
        
        self.transform = transforms.Compose([
            transforms.ToTensor(),
        ])

    def __len__(self):
        return self.length

    def generate_random_text(self):
        chars = "1234567890+=XYZabcABC算式解答選擇題填空題為何如此這般"
        length = random.randint(5, 15)
        return "".join(random.choices(chars, k=length))

    def add_handwriting(self, clean_img):
        img = clean_img.convert("RGBA")
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 模擬手寫文字
        num_hw_lines = random.randint(3, 10)
        font_path = random.choice(self.hw_fonts) if self.hw_fonts else None
        for _ in range(num_hw_lines):
            if font_path:
                # 大小變化極大，涵蓋小字與超大字
                font_size = random.randint(20, 150)
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except:
                    font = ImageFont.load_default()
            else:
                font = ImageFont.load_default()
            
            text = self.generate_random_text()
            x = random.randint(10, self.patch_size - 100)
            y = random.randint(10, self.patch_size - 50)
            
            # 手寫字顏色變化 (涵蓋極深黑色到淺灰)
            stroke_color = random.randint(0, 150)
            alpha = random.randint(150, 255)
            
            txt_img = Image.new('RGBA', (self.patch_size, self.patch_size), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            
            # 隨機產生從極細 (原子筆) 到極粗 (奇異筆) 的筆劃
            thickness = random.randint(0, 10)
            try:
                txt_draw.text((x, y), text, fill=(stroke_color, stroke_color, stroke_color, alpha), font=font, stroke_width=thickness, stroke_fill=(stroke_color, stroke_color, stroke_color, alpha))
            except:
                txt_draw.text((x, y), text, fill=(stroke_color, stroke_color, stroke_color, alpha), font=font)
            
            angle = random.uniform(-25, 25)
            txt_img = txt_img.rotate(angle, resample=Image.BICUBIC, center=(x, y))
            overlay = Image.alpha_composite(overlay, txt_img)

        # 模擬隨機線條與圈選
        draw = ImageDraw.Draw(overlay)
        num_strokes = random.randint(3, 12)
        for _ in range(num_strokes):
            stroke_color = random.randint(0, 120)
            alpha = random.randint(120, 255)
            # 隨機產生從極細到極粗的線條 (1 到 15 像素)
            width = random.randint(1, 15)
            
            points = []
            num_points = random.randint(3, 8)
            for _ in range(num_points):
                points.append((random.randint(0, self.patch_size), random.randint(0, self.patch_size)))
            
            draw.line(points, fill=(stroke_color, stroke_color, stroke_color, alpha), width=width, joint="curve")
            
            if random.random() < 0.5:
                x = random.randint(50, self.patch_size - 50)
                y = random.randint(50, self.patch_size - 50)
                r = random.randint(20, 80)
                draw.ellipse([x-r, y-r, x+r, y+r], outline=(stroke_color, stroke_color, stroke_color, alpha), width=random.randint(1, 10))
                
        # 隨機決定暈染程度，涵蓋不暈染到嚴重暈染
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.1, 2.5)))
        out_img = Image.alpha_composite(img, overlay).convert("L")
            
        return out_img

    def __getitem__(self, idx):
        bg_idx = random.randint(0, len(self.backgrounds) - 1)
        bg_img = self.backgrounds[bg_idx]
        
        w, h = bg_img.size
        x = random.randint(0, max(0, w - self.patch_size))
        y = random.randint(0, max(0, h - self.patch_size))
        clean_patch = bg_img.crop((x, y, x + self.patch_size, y + self.patch_size))
        
        dirty_patch = self.add_handwriting(clean_patch)
        
        if random.random() < 0.5:
            arr = np.array(dirty_patch, dtype=np.float32)
            noise = np.random.normal(0, random.uniform(2, 10), arr.shape)
            arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
            dirty_patch = Image.fromarray(arr)
        
        return self.transform(dirty_patch), self.transform(clean_patch)

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = MobileNetV3UNet().to(device)
    batch_size = 32 # 依照要求改回原本的 32
    
    dataset = HybridDataset(target_dir="../real_data/target", patch_size=512, length=2000)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    criterion = CompositeLoss().to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=2e-4) 
    scheduler = CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
    
    # 載入被公認表現最好的第 55 輪權重，並從這裡重新出發
    ckpt_path = "checkpoints/model_epoch_55.pth"
    start_epoch = 55
    if os.path.exists(ckpt_path):
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        print(f"Resuming from {ckpt_path} for Thicker Hybrid Training (Conservative Loss)...")
    else:
        print("Cannot find model_epoch_55.pth!")
        return
    
    target_epochs = start_epoch + 1000 # 無限期訓練 1000 輪
    
    for epoch in range(start_epoch, target_epochs):
        model.train()
        epoch_loss = 0.0
        
        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            
            loss, _, _, _ = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
            if batch_idx % 10 == 0:
                print(f"Hybrid Epoch [{epoch+1}/{target_epochs}] Batch [{batch_idx}/{len(dataloader)}] Loss: {loss.item():.4f}")
                
        scheduler.step()
        print(f"Hybrid Epoch [{epoch+1}/{target_epochs}] Avg Loss: {epoch_loss/len(dataloader):.4f}")
        torch.save(model.state_dict(), f"checkpoints/model_epoch_{epoch+1}.pth")
        
    print("Hybrid Training Complete!")

if __name__ == "__main__":
    main()
