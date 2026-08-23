import os
import random
import torch
from torch.utils.data import Dataset
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import torchvision.transforms as transforms

class SyntheticExamDataset(Dataset):
    def __init__(self, length=200000, patch_size=512):
        self.length = length
        self.patch_size = patch_size
        
        # 印刷字體 (Target)
        self.print_fonts = [
            'assets/fonts/NotoSansTC-Regular.otf',
            'assets/fonts/NotoSerifTC-Regular.otf',
            'C:\\Windows\\Fonts\\kaiu.ttf',     # 如果本機有標楷體
            'C:\\Windows\\Fonts\\mingliu.ttc'   # 如果本機有新細明體
        ]
        self.print_fonts = [f for f in self.print_fonts if os.path.exists(f)]
        
        # 手寫字體 (模擬 CASIA-HWDB 等手寫字)
        self.hw_fonts = [
            'assets/fonts/ChenYuluoyan-Thin.ttf',
            'assets/fonts/setofont.ttf'
        ]
        self.hw_fonts = [f for f in self.hw_fonts if os.path.exists(f)]
        
        self.transform = transforms.Compose([
            transforms.ToTensor(), # 正規化到 [0, 1]
        ])

    def __len__(self):
        return self.length

    def generate_random_text(self, hw=False):
        chars = "這是一段測試文字用來模擬考卷上的題目或是學生寫的筆記與算式1234567890+=XYZabc為何如此這般"
        length = random.randint(5, 15) if hw else random.randint(10, 30)
        return "".join(random.choices(chars, k=length))

    def create_clean_background(self):
        # 產生純淨的白色或淺灰背景
        bg_color = random.randint(240, 255)
        img = Image.new('L', (self.patch_size, self.patch_size), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # 隨機繪製完美幾何圖形/圖表 (教導 AI 保留圖表)
        if random.random() < 0.4:
            chart_type = random.choice(['grid', 'axes', 'shapes'])
            if chart_type == 'grid':
                # 繪製方格網底
                step = random.randint(20, 50)
                for i in range(0, self.patch_size, step):
                    draw.line([(0, i), (self.patch_size, i)], fill=random.randint(100, 200), width=1)
                    draw.line([(i, 0), (i, self.patch_size)], fill=random.randint(100, 200), width=1)
            elif chart_type == 'axes':
                # 繪製 XY 坐標軸
                cx, cy = random.randint(100, 400), random.randint(100, 400)
                draw.line([(cx, 0), (cx, self.patch_size)], fill=0, width=random.randint(1, 2))
                draw.line([(0, cy), (self.patch_size, cy)], fill=0, width=random.randint(1, 2))
                # 畫幾條完美的折線
                draw.line([(cx, cy), (cx+100, cy-100), (cx+200, cy-50)], fill=random.randint(0, 50), width=2)
            elif chart_type == 'shapes':
                # 繪製完美的圓形與矩形
                x, y = random.randint(50, 300), random.randint(50, 300)
                r = random.randint(50, 150)
                draw.ellipse([x, y, x+r, y+r], outline=0, width=2)
                draw.rectangle([x-50, y-50, x+50, y+50], outline=0, width=2)

        # 隨機繪製一些橫線 (模擬筆記本或底線)
        elif random.random() < 0.3:
            y_start = random.randint(50, 100)
            for y in range(y_start, self.patch_size, 50):
                draw.line([(0, y), (self.patch_size, y)], fill=random.randint(150, 200), width=random.randint(1, 2))
                
        # 隨機繪製印刷文字
        font_path = random.choice(self.print_fonts) if self.print_fonts else None
        num_lines = random.randint(3, 8)
        
        for i in range(num_lines):
            try:
                font_size = random.randint(20, 35)
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
                
            text = self.generate_random_text()
            x = random.randint(10, 50)
            y = 30 + i * 50 + random.randint(-10, 10)
            draw.text((x, y), text, fill=random.randint(0, 50), font=font)
            
        return img

    def add_handwriting(self, clean_img):
        # 將純淨影像轉為 RGBA 以支援透明度混合
        img = clean_img.convert("RGBA")
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 1. 模擬手寫文字 (使用手寫字體)
        num_hw_lines = random.randint(2, 6)
        font_path = random.choice(self.hw_fonts) if self.hw_fonts else None
        for _ in range(num_hw_lines):
            if font_path:
                font_size = random.randint(25, 45)
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except:
                    font = ImageFont.load_default()
            else:
                font = ImageFont.load_default()
            
            text = self.generate_random_text(hw=True)
            x = random.randint(10, self.patch_size - 100)
            y = random.randint(10, self.patch_size - 50)
            
            # 手寫字通常比較不那麼黑 (深灰色) 且帶有一點透明度
            stroke_color = random.randint(20, 100)
            alpha = random.randint(180, 255)
            
            # 建立一個單獨的圖片來繪製文字以便旋轉
            txt_img = Image.new('RGBA', (self.patch_size, self.patch_size), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((x, y), text, fill=(stroke_color, stroke_color, stroke_color, alpha), font=font)
            
            # 隨機旋轉
            angle = random.uniform(-15, 15)
            txt_img = txt_img.rotate(angle, resample=Image.BICUBIC, center=(x, y))
            
            # 疊加上去
            overlay = Image.alpha_composite(overlay, txt_img)

        # 2. 模擬隨機線條與圈選
        draw = ImageDraw.Draw(overlay)
        num_strokes = random.randint(2, 5)
        for _ in range(num_strokes):
            stroke_color = random.randint(30, 120)
            alpha = random.randint(150, 255)
            width = random.randint(1, 4)
            
            points = []
            num_points = random.randint(3, 8)
            for _ in range(num_points):
                points.append((random.randint(0, self.patch_size), random.randint(0, self.patch_size)))
            
            draw.line(points, fill=(stroke_color, stroke_color, stroke_color, alpha), width=width, joint="curve")
            
            if random.random() < 0.5:
                x = random.randint(50, self.patch_size - 50)
                y = random.randint(50, self.patch_size - 50)
                r = random.randint(20, 50)
                draw.ellipse([x-r, y-r, x+r, y+r], outline=(stroke_color, stroke_color, stroke_color, alpha), width=random.randint(2, 4))
                
        # 稍微對手寫層做高斯模糊，模擬原子筆暈染
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))
        
        # 合成影像
        out_img = Image.alpha_composite(img, overlay).convert("L")
        return out_img

    def __getitem__(self, idx):
        clean_img = self.create_clean_background()
        dirty_img = self.add_handwriting(clean_img)
        
        input_tensor = self.transform(dirty_img)
        target_tensor = self.transform(clean_img)
        
        return input_tensor, target_tensor

if __name__ == "__main__":
    dataset = SyntheticExamDataset(length=10)
    inp, tgt = dataset[0]
    
    transforms.ToPILImage()(inp).save("test_input.png")
    transforms.ToPILImage()(tgt).save("test_target.png")
    print("Test images saved as test_input.png and test_target.png")

