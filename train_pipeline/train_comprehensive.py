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
    
    # 建立綜合資料集 (Comprehensive Dataset)
    # 1. 純合成資料 (長條圖、拋物線、白底，培養廣泛泛化能力)
    synth_dataset = SyntheticExamDataset(length=2000, patch_size=512)
    
    # 2. 混合真實資料 (真實考卷底圖 + 極粗黑假手寫，專精真實場景與黑筆對抗)
    hybrid_dataset = HybridDataset(target_dir="../real_data/target", patch_size=512, length=2000)
    
    # 將兩者合併，確保模型既不忘記廣泛圖表，又精通真實考卷
    comprehensive_dataset = ConcatDataset([synth_dataset, hybrid_dataset])
    
    # DataLoader 會自動打亂這兩批資料
    batch_size = 32
    dataloader = DataLoader(comprehensive_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    # 載入模型
    model = MobileNetV3UNet().to(device)
    
    # 載入第 55 輪權重繼續訓練
    ckpt_path = "checkpoints/model_epoch_55.pth"
    start_epoch = 55
    if os.path.exists(ckpt_path):
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        print(f"Resuming from {ckpt_path} for COMPREHENSIVE Training...")
    else:
        print("Cannot find model_epoch_55.pth, starting from scratch...")
        start_epoch = 0

    criterion = CompositeLoss().to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-4) 
    scheduler = CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
    
    target_epochs = start_epoch + 1000 # 綜合特訓 1000 輪
    
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
                print(f"Comprehensive Epoch [{epoch+1}/{target_epochs}] Batch [{batch_idx}/{len(dataloader)}] Loss: {loss.item():.4f}")
                
        scheduler.step()
        print(f"Comprehensive Epoch [{epoch+1}/{target_epochs}] Avg Loss: {epoch_loss/len(dataloader):.4f}")
        torch.save(model.state_dict(), f"checkpoints/model_epoch_{epoch+1}.pth")
        
    print("Comprehensive Training Complete!")

if __name__ == "__main__":
    main()
