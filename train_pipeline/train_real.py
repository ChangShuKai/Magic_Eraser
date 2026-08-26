import os
import glob
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import torchvision.transforms as transforms
from torch.optim.lr_scheduler import CosineAnnealingLR

# 限制 CPU 執行緒
torch.set_num_threads(2)

from model import MobileNetV3UNet
from loss import CompositeLoss

class RealExamDataset(Dataset):
    def __init__(self, input_dir, target_dir, patch_size=512, length=1000):
        self.patch_size = patch_size
        self.length = length
        self.inputs = []
        self.targets = []
        
        # 讀取所有圖片檔路徑
        input_files = []
        target_files = []
        for tgt_p in sorted(glob.glob(os.path.join(target_dir, "*.*"))):
            basename = os.path.basename(tgt_p)
            inp_p = os.path.join(input_dir, basename)
            if os.path.exists(inp_p):
                input_files.append(inp_p)
                target_files.append(tgt_p)
        
        # 將所有圖片載入記憶體
        print("Loading real data into memory...")
        for inp_p, tgt_p in zip(input_files, target_files):
            inp_img = Image.open(inp_p).convert("L")
            tgt_img = Image.open(tgt_p).convert("L")
            self.inputs.append(inp_img)
            self.targets.append(tgt_img)
        print(f"Loaded {len(self.inputs)} real image pairs.")
            
        self.transform = transforms.Compose([
            transforms.ToTensor(),
        ])

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        # 隨機選一張圖
        img_idx = random.randint(0, len(self.inputs) - 1)
        inp_img = self.inputs[img_idx]
        tgt_img = self.targets[img_idx]
        
        # 隨機裁切 512x512
        w, h = inp_img.size
        x = random.randint(0, max(0, w - self.patch_size))
        y = random.randint(0, max(0, h - self.patch_size))
        
        inp_patch = inp_img.crop((x, y, x + self.patch_size, y + self.patch_size))
        tgt_patch = tgt_img.crop((x, y, x + self.patch_size, y + self.patch_size))
        
        # 隨機旋轉
        angle = random.choice([0, 90, 180, 270])
        if angle != 0:
            inp_patch = inp_patch.rotate(angle)
            tgt_patch = tgt_patch.rotate(angle)
            
        # 隨機水平翻轉
        if random.random() > 0.5:
            inp_patch = inp_patch.transpose(Image.FLIP_LEFT_RIGHT)
            tgt_patch = tgt_patch.transpose(Image.FLIP_LEFT_RIGHT)
            
        return self.transform(inp_patch), self.transform(tgt_patch)

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = MobileNetV3UNet().to(device)
    batch_size = 32
    
    dataset = RealExamDataset(
        input_dir="../real_data/input", 
        target_dir="../real_data/target_aligned", 
        patch_size=512, 
        length=2000
    )
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    criterion = CompositeLoss().to(device)
    
    # 微調學習率降低
    optimizer = optim.Adam(model.parameters(), lr=1e-4) 
    scheduler = CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
    
    start_epoch = 40
    ckpt_path = f"checkpoints/model_epoch_{start_epoch}.pth"
    if os.path.exists(ckpt_path):
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        print(f"Resuming for ALIGNED REAL DATA from {ckpt_path} (Epoch {start_epoch})")
    
    target_epochs = start_epoch + 15 # 微調 15 輪
    
    for epoch in range(start_epoch, target_epochs):
        model.train()
        epoch_loss = 0.0
        
        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            
            loss, loss_l1, loss_ssim, loss_sobel = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
            if batch_idx % 10 == 0:
                print(f"Fine-tune Epoch [{epoch+1}/{target_epochs}] Batch [{batch_idx}/{len(dataloader)}] "
                      f"Loss: {loss.item():.4f}")
                
        scheduler.step()
        print(f"Fine-tune Epoch [{epoch+1}/{target_epochs}] Avg Loss: {epoch_loss/len(dataloader):.4f}")
        torch.save(model.state_dict(), f"checkpoints/model_epoch_{epoch+1}.pth")
        
    print("Real Data Fine-tuning Complete!")

if __name__ == "__main__":
    main()
