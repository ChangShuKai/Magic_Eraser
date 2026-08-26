import torch
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import os

# 強制限制 PyTorch 只使用 2 個 CPU 執行緒，避免佔用大量 CPU 資源
torch.set_num_threads(2)

from model import MobileNetV3UNet
from loss import CompositeLoss
from data_synthesis import SyntheticExamDataset

def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # 建立模型
    model = MobileNetV3UNet().to(device)
    
    # 建立 DataLoader
    batch_size = 32 # 依照要求提高到 32，佔用約 6~7GB GPU VRAM
    dataset = SyntheticExamDataset(length=10000, patch_size=512)    
    # 強制使用單執行緒 (num_workers=0)，絕對不佔用額外的系統 RAM 與 CPU
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    # 損失函數與優化器
    criterion = CompositeLoss(lambda_l1=1.0, lambda_ssim=0.5, lambda_sobel=0.5).to(device)
    optimizer = AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
    
    epochs = 10
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)
    
    # 建立儲存資料夾
    os.makedirs('checkpoints', exist_ok=True)
    
    # 尋找最新的 checkpoint 以接續訓練
    start_epoch = 0
    import glob
    checkpoints = glob.glob('checkpoints/model_epoch_*.pth')
    if checkpoints:
        # 找出數字最大的 epoch
        latest_ckpt = max(checkpoints, key=lambda x: int(x.split('_')[-1].split('.')[0]))
        start_epoch = int(latest_ckpt.split('_')[-1].split('.')[0])
        model.load_state_dict(torch.load(latest_ckpt, map_location=device))
        print(f"Resuming training from {latest_ckpt} (Epoch {start_epoch})")
    # 放開限制，進行馬拉松式長期訓練 (額外訓練 100 輪)
    target_epochs = start_epoch + 100
    
    # 訓練迴圈
    for epoch in range(start_epoch, target_epochs):
        model.train()
        epoch_loss = 0.0
        
        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            
            loss, l1, ssim_loss, sobel = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
            if batch_idx % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}] Batch [{batch_idx}/{len(dataloader)}] Loss: {loss.item():.4f} (L1: {l1.item():.4f}, SSIM: {ssim_loss.item():.4f}, Sobel: {sobel.item():.4f})")
                
        scheduler.step()
        avg_loss = epoch_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{epochs}] Average Loss: {avg_loss:.4f}, LR: {scheduler.get_last_lr()[0]:.6f}")
        
        # 儲存 Checkpoint
        torch.save(model.state_dict(), f"checkpoints/model_epoch_{epoch+1}.pth")
        
    print("Training Complete!")

if __name__ == "__main__":
    train()
