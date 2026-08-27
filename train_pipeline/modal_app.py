import modal
import torch
import torchvision.transforms as T
from PIL import Image
import io
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

# 定義模型類別
class MobileNetV3UNet(nn.Module):
    def __init__(self):
        super(MobileNetV3UNet, self).__init__()
        
        # Load pretrained MobileNetV3-Small
        backbone = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT).features
        
        # Modify the first convolutional layer to accept 1 channel
        original_conv1 = backbone[0][0]
        self.conv1 = nn.Conv2d(1, original_conv1.out_channels, 
                               kernel_size=original_conv1.kernel_size, 
                               stride=original_conv1.stride, 
                               padding=original_conv1.padding, 
                               bias=False)
        with torch.no_grad():
            self.conv1.weight = nn.Parameter(original_conv1.weight.mean(dim=1, keepdim=True))
            
        # Encoder parts
        self.enc1 = nn.Sequential(self.conv1, backbone[0][1], backbone[0][2])
        self.enc2 = backbone[1]
        self.enc3 = nn.Sequential(backbone[2], backbone[3])
        self.enc4 = nn.Sequential(backbone[4], backbone[5], backbone[6], backbone[7], backbone[8])
        self.enc5 = nn.Sequential(backbone[9], backbone[10], backbone[11])
        
        # Decoder parts with Skip Connections
        self.up4 = nn.ConvTranspose2d(96, 48, kernel_size=2, stride=2)
        self.dec4 = nn.Sequential(
            nn.Conv2d(48 + 48, 48, kernel_size=3, padding=1),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )

        self.up3 = nn.ConvTranspose2d(48, 24, kernel_size=2, stride=2)
        self.dec3 = nn.Sequential(
            nn.Conv2d(24 + 24, 24, kernel_size=3, padding=1),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True)
        )
        
        self.up2 = nn.ConvTranspose2d(24, 16, kernel_size=2, stride=2)
        self.dec2 = nn.Sequential(
            nn.Conv2d(16 + 16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True)
        )
        
        self.up1 = nn.ConvTranspose2d(16, 16, kernel_size=2, stride=2)
        self.dec1 = nn.Sequential(
            nn.Conv2d(16 + 16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True)
        )
        
        self.up0 = nn.ConvTranspose2d(16, 16, kernel_size=2, stride=2)
        
        self.out_conv = nn.Sequential(
            nn.Conv2d(16, 1, kernel_size=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)
        e5 = self.enc5(e4)
        
        d4 = self.up4(e5)
        d4 = torch.cat([d4, e4], dim=1)
        d4 = self.dec4(d4)

        d3 = self.up3(d4)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)
        
        d2 = self.up2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)
        
        d1 = self.up1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)
        
        d0 = self.up0(d1)
        out = self.out_conv(d0)
        
        return out

import os
import glob

latest_pth = ""
# 尋找最新的模型權重檔 (只在本地端尋找並上傳，雲端不需要)
checkpoint_dir = os.path.join(os.path.dirname(__file__), "checkpoints")
if os.path.exists(checkpoint_dir):
    pth_files = glob.glob(os.path.join(checkpoint_dir, "model_epoch_*.pth"))
    if pth_files:
        def get_epoch_num(f):
            try:
                basename = os.path.basename(f)
                return int(basename.replace("model_epoch_", "").replace(".pth", ""))
            except:
                return -1
        latest_pth = max(pth_files, key=get_epoch_num)
        print(f"Deploying with latest model: {latest_pth}")

# 1. 定義雲端執行環境與安裝套件
app = modal.App("exam-cleaner")

image = (
    modal.Image.debian_slim()
    .pip_install("torch", "torchvision", "pillow", "fastapi[standard]", "opencv-python-headless", "numpy", "python-multipart")
)
if latest_pth:
    image = image.add_local_file(latest_pth, remote_path="/root/model.pth")

# 把外層的 image_processor.py 也傳上 Modal 雲端，讓 Modal 也能跑純 HSV
import sys
parent_dir = os.path.dirname(os.path.dirname(__file__))
image_processor_path = os.path.join(parent_dir, "image_processor.py")
if os.path.exists(image_processor_path):
    image = image.add_local_file(image_processor_path, remote_path="/root/image_processor.py")

# 2. 建立 FastAPI 實例並開啟 CORS（讓 Vercel 前端可以正常呼叫）
web_app = FastAPI()
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 定義 GPU 模型類別
@app.cls(
    gpu="L4",                    # 使用 L4 GPU，因為 T4 容量不足
    image=image,
    max_containers=100,
    timeout=60,
    min_containers=1
)
@modal.concurrent(max_inputs=15)  # 新版寫法：單台機器可同時並發處理 15 個請求
class CleanerService:
    @modal.enter()
    def load_model(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = MobileNetV3UNet()
        self.model.load_state_dict(torch.load("/root/model.pth", map_location=self.device))
        self.model.to(self.device).eval()

    @modal.fastapi_endpoint(method="POST")
    async def clean_image(
        self, 
        image: UploadFile = File(...),
        color_type: str = Form("both"),
        fill_method: str = Form("white"),
        enhance: str = Form("false")
    ):
        img_bytes = await image.read()
        
        # 如果是純 HSV 去除顏色 (fill_method == 'white')
        if fill_method == 'white':
            import sys
            if "/root" not in sys.path:
                sys.path.append("/root")
            import cv2
            import numpy as np
            try:
                from image_processor import process_image, enhance_text, whiten_background
            except ImportError:
                return Response(content=b"image_processor not found on Modal", status_code=500)
            
            # 讀取圖片
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 純 HSV 處理
            img_cv = whiten_background(img_cv)
            img_cv = process_image(img_cv, color_type=color_type, tolerance=50, fill_method='white')
            if enhance.lower() == 'true':
                img_cv = enhance_text(img_cv)
                
            is_success, im_buf_arr = cv2.imencode(".jpg", img_cv, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return Response(content=im_buf_arr.tobytes(), media_type="image/jpeg")

        # 否則使用 AI 智慧修補 (inpaint)
        # 讀取前端上傳的圖片 (轉為 L 灰階，因為模型吃單通道)
        img = Image.open(io.BytesIO(img_bytes)).convert("L")
        
        # 影像前處理
        transform = T.ToTensor()
        input_tensor = transform(img).unsqueeze(0).to(self.device)
        
        # 動態補邊 (Padding) 讓長寬都是 32 的倍數，避免 UNet skip connection 的維度不匹配問題
        _, _, h, w = input_tensor.size()
        pad_h = (32 - (h % 32)) % 32
        pad_w = (32 - (w % 32)) % 32
        if pad_h > 0 or pad_w > 0:
            import torch.nn.functional as F
            # padding 順序為 (左, 右, 上, 下)
            input_tensor = F.pad(input_tensor, (0, pad_w, 0, pad_h), mode='reflect')

        # 極速推論 (FP16)
        with torch.inference_mode():
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                output_tensor = self.model(input_tensor)
                
        # 切割回原始圖片大小
        if pad_h > 0 or pad_w > 0:
            output_tensor = output_tensor[:, :, :h, :w]

        # 後處理回傳乾淨圖片 (轉回 3 通道給前端或維持灰階)
        output_tensor = output_tensor.squeeze(0).clamp(0, 1).cpu()
        out_img = T.ToPILImage()(output_tensor)
        out_img = out_img.convert("RGB")

        buffer = io.BytesIO()
        out_img.save(buffer, format="JPEG", quality=92)
        return Response(content=buffer.getvalue(), media_type="image/jpeg")

