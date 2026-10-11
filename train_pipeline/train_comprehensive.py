import os
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, ConcatDataset
from torch.optim.lr_scheduler import CosineAnnealingLR

# 限制 CPU 執行緒
torch.set_num_threads(2)

from model import MobileNetV3UNet
from loss import CompositeLoss
from data_synthesis import SyntheticExamDataset
from train_hybrid import HybridDataset

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 限制 RTX 3060 最多只使用 30% VRAM，讓出空間給其他使用者
    if torch.cuda.is_available():
        torch.cuda.set_per_process_memory_fraction(0.3, 0)
        print("GPU Memory limited to 30% (Max ~3.6GB on RTX 3060).")
    
    # 建立綜合資料集 (Comprehensive Dataset)
    # 1. 純合成資料 (長條圖、拋物線、白底，培養廣泛泛化能力)
    synth_dataset = SyntheticExamDataset(length=250, patch_size=512)
    
    # 2. 混合真實資料 (真實考卷底圖 + 極粗黑假手寫，專精真實場景與黑筆對抗)
    hybrid_dataset = HybridDataset(target_dir="../real_data/target", patch_size=512, length=250)
    
    # 將兩者合併，確保模型既不忘記廣泛圖表，又精通真實考卷
    comprehensive_dataset = ConcatDataset([synth_dataset, hybrid_dataset])
    
    # DataLoader 會自動打亂這兩批資料
    # 因應 VRAM 30% 限制，將 batch_size 降至 2
    batch_size = 2
    dataloader = DataLoader(comprehensive_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    # 載入模型
    model = MobileNetV3UNet().to(device)
    
    import glob
    checkpoints = glob.glob('checkpoints/model_epoch_*.pth')
    start_epoch = 0
    if checkpoints:
        latest_ckpt = max(checkpoints, key=lambda x: int(x.split('_')[-1].split('.')[0]))
        start_epoch = int(latest_ckpt.split('_')[-1].split('.')[0])
        model.load_state_dict(torch.load(latest_ckpt, map_location=device))
        print(f"Resuming from {latest_ckpt} (Epoch {start_epoch}) for COMPREHENSIVE Training...")
    else:
        print("Cannot find any checkpoints, starting from scratch...")

    criterion = CompositeLoss().to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-4) 
    scheduler = CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
    
    target_epochs = start_epoch + 1000 # 綜合特訓 1000 輪
    
    import time
    for epoch in range(start_epoch, target_epochs):
        model.train()
        epoch_loss = 0.0
        
        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            
            loss, _, _, _, _ = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
            # 強制暫停 0.5 秒，降低 GPU 使用率，避免長期佔滿 100% 運算力
            time.sleep(0.5)
            
            if batch_idx % 10 == 0:
                print(f"Comprehensive Epoch [{epoch+1}/{target_epochs}] Batch [{batch_idx}/{len(dataloader)}] Loss: {loss.item():.4f}")
                
        scheduler.step()
        # 儲存 Checkpoint 並刪除舊版，只保留最新一版
        new_ckpt = f"checkpoints/model_epoch_{epoch+1}.pth"
        torch.save(model.state_dict(), new_ckpt)
        for old_ckpt in glob.glob("checkpoints/model_epoch_*.pth"):
            if os.path.abspath(old_ckpt) != os.path.abspath(new_ckpt):
                try:
                    os.remove(old_ckpt)
                except Exception as e:
                    print(f"Warning: Failed to delete old checkpoint {old_ckpt}: {e}")
        
    print("Comprehensive Training Complete!")

if __name__ == "__main__":
    main()
