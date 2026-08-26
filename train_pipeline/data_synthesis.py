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
        if random.random() < 0.6:  # 提高出現圖表的機率到 60%
            chart_type = random.choice(['grid', 'axes', 'shapes', 'bar_chart', 'parabola', 'scatter'])
            if chart_type == 'grid':
                # 繪製方格網底
                step = random.randint(10, 30)
                for i in range(0, self.patch_size, step):
                    draw.line([(0, i), (self.patch_size, i)], fill=random.randint(50, 150), width=1)
                    draw.line([(i, 0), (i, self.patch_size)], fill=random.randint(50, 150), width=1)
            elif chart_type == 'axes':
                # 繪製帶有刻度的 XY 坐標軸與折線
                cx, cy = random.randint(100, 400), random.randint(100, 400)
                draw.line([(cx, 0), (cx, self.patch_size)], fill=0, width=2)
                draw.line([(0, cy), (self.patch_size, cy)], fill=0, width=2)
                # 畫刻度
                for tick in range(0, self.patch_size, 20):
                    draw.line([(cx-5, tick), (cx+5, tick)], fill=0, width=1)
                    draw.line([(tick, cy-5), (tick, cy+5)], fill=0, width=1)
                # 畫多條複雜折線
                points = [(random.randint(0, self.patch_size), random.randint(0, self.patch_size)) for _ in range(5)]
                points.sort(key=lambda p: p[0])
                draw.line(points, fill=random.randint(0, 100), width=random.randint(1, 3))
            elif chart_type == 'shapes':
                # 繪製幾何圖形 (包含填滿與空心)
                for _ in range(random.randint(2, 5)):
                    x, y = random.randint(50, 400), random.randint(50, 400)
                    r = random.randint(30, 100)
                    if random.random() > 0.5:
                        draw.ellipse([x, y, x+r, y+r], outline=0, width=2)
                    else:
                        draw.rectangle([x, y, x+r, y+r], fill=random.randint(150, 220), outline=0, width=2)
            elif chart_type == 'bar_chart':
                # 繪製直方圖/長條圖
                base_y = random.randint(300, 450)
                draw.line([(50, base_y), (450, base_y)], fill=0, width=2)
                for bx in range(70, 400, 40):
                    h = random.randint(20, 200)
                    draw.rectangle([bx, base_y-h, bx+20, base_y], fill=random.randint(50, 200), outline=0, width=1)
            elif chart_type == 'parabola':
                # 繪製平滑的拋物線 (函數圖形)
                cx, cy = random.randint(200, 300), random.randint(300, 450)
                draw.line([(cx, 0), (cx, self.patch_size)], fill=0, width=2)
                draw.line([(0, cy), (self.patch_size, cy)], fill=0, width=2)
                a = random.uniform(-0.02, 0.02)
                curve_points = []
                for px in range(0, self.patch_size, 5):
                    dx = px - cx
                    py = cy - int(a * dx * dx)
                    if 0 <= py <= self.patch_size:
                        curve_points.append((px, py))
                if len(curve_points) > 2:
                    draw.line(curve_points, fill=0, width=2)
            elif chart_type == 'scatter':
                # 繪製散佈圖 (密集的點)
                cx, cy = random.randint(100, 400), random.randint(100, 400)
                draw.line([(cx, 0), (cx, self.patch_size)], fill=0, width=2)
                draw.line([(0, cy), (self.patch_size, cy)], fill=0, width=2)
                for _ in range(random.randint(30, 100)):
                    px, py = random.randint(50, 450), random.randint(50, 450)
                    r = random.randint(2, 5)
                    if random.random() > 0.5:
                        draw.ellipse([px-r, py-r, px+r, py+r], fill=0)
                    else:
                        draw.polygon([(px, py-r), (px-r, py+r), (px+r, py+r)], fill=0)

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
            # 讓印刷字體的顏色有深淺變化 (不要永遠是純黑，模擬掃描的灰色)
            draw.text((x, y), text, fill=random.randint(0, 120), font=font)
            
        # 對乾淨背景加入輕微的高斯模糊，模擬真實考卷掃描的模糊感
        if random.random() < 0.8:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.1, 0.7)))
            
        return img

    def add_handwriting(self, clean_img):
        # 將純淨影像轉為 RGBA 以支援透明度混合
        img = clean_img.convert("RGBA")
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 1. 模擬手寫文字 (使用手寫字體)
        num_hw_lines = random.randint(2, 8)
        font_path = random.choice(self.hw_fonts) if self.hw_fonts else None
        for _ in range(num_hw_lines):
            if font_path:
                font_size = random.randint(20, 50) # 手寫字體大小變化更大
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except:
                    font = ImageFont.load_default()
            else:
                font = ImageFont.load_default()
            
            text = self.generate_random_text(hw=True)
            x = random.randint(10, self.patch_size - 100)
            y = random.randint(10, self.patch_size - 50)
            
            # 手寫字顏色變化 (包含極深的黑色，模擬黑筆)
            stroke_color = random.randint(0, 150)
            alpha = random.randint(150, 255)
            
            # 建立一個單獨的圖片來繪製文字以便旋轉
            txt_img = Image.new('RGBA', (self.patch_size, self.patch_size), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            
            # 使用 stroke_width 模擬不同粗細的筆
            try:
                txt_draw.text((x, y), text, fill=(stroke_color, stroke_color, stroke_color, alpha), font=font, stroke_width=random.randint(0, 2), stroke_fill=(stroke_color, stroke_color, stroke_color, alpha))
            except:
                txt_draw.text((x, y), text, fill=(stroke_color, stroke_color, stroke_color, alpha), font=font)
            
            # 隨機旋轉
            angle = random.uniform(-25, 25)
            txt_img = txt_img.rotate(angle, resample=Image.BICUBIC, center=(x, y))
            
            # 疊加上去
            overlay = Image.alpha_composite(overlay, txt_img)

        # 2. 模擬隨機線條與圈選
        draw = ImageDraw.Draw(overlay)
        num_strokes = random.randint(3, 8)
        for _ in range(num_strokes):
            stroke_color = random.randint(0, 120)
            alpha = random.randint(120, 255)
            width = random.randint(1, 6) # 模擬更粗的筆劃
            
            points = []
            num_points = random.randint(3, 8)
            for _ in range(num_points):
                points.append((random.randint(0, self.patch_size), random.randint(0, self.patch_size)))
            
            draw.line(points, fill=(stroke_color, stroke_color, stroke_color, alpha), width=width, joint="curve")
            
            if random.random() < 0.5:
                x = random.randint(50, self.patch_size - 50)
                y = random.randint(50, self.patch_size - 50)
                r = random.randint(20, 60)
                draw.ellipse([x-r, y-r, x+r, y+r], outline=(stroke_color, stroke_color, stroke_color, alpha), width=random.randint(2, 6))
                
        # 稍微對手寫層做高斯模糊，模擬原子筆暈染
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.2)))
        
        # 合成影像
        out_img = Image.alpha_composite(img, overlay).convert("L")
        
        # 對最終影像加入隨機噪點 (JPEG artifacts 模擬)
        if random.random() < 0.5:
            arr = np.array(out_img, dtype=np.float32)
            noise = np.random.normal(0, random.uniform(2, 10), arr.shape)
            arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
            out_img = Image.fromarray(arr)
            
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

