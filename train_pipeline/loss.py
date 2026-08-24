import torch
import torch.nn as nn
import torch.nn.functional as F

def gaussian_window(window_size, sigma):
    coords = torch.arange(window_size, dtype=torch.float32)
    coords -= window_size // 2
    g = torch.exp(-(coords**2) / (2 * sigma**2))
    g /= g.sum()
    return g.view(1, -1) * g.view(-1, 1)

def ssim(img1, img2, window_size=11, size_average=True):
    channel = img1.size(1)
    window = gaussian_window(window_size, 1.5).unsqueeze(0).unsqueeze(0).expand(channel, 1, window_size, window_size).to(img1.device)
    
    mu1 = F.conv2d(img1, window, padding=window_size//2, groups=channel)
    mu2 = F.conv2d(img2, window, padding=window_size//2, groups=channel)
    
    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2
    
    sigma1_sq = F.conv2d(img1 * img1, window, padding=window_size//2, groups=channel) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=window_size//2, groups=channel) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=window_size//2, groups=channel) - mu1_mu2
    
    C1 = 0.01 ** 2
    C2 = 0.03 ** 2
    
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    
    if size_average:
        return ssim_map.mean()
    else:
        return ssim_map.mean(1).mean(1).mean(1)

class CompositeLoss(nn.Module):
    def __init__(self, lambda_l1=1.0, lambda_ssim=0.5, lambda_sobel=0.5):
        super(CompositeLoss, self).__init__()
        self.l1 = nn.L1Loss()
        
        # 調整權重：讓模型更重視「保留原始結構(SSIM)」與「邊緣(Sobel)」，降低背景留白的壓力
        self.lambda_l1 = 0.5    # 原本是 1.0
        self.lambda_ssim = 1.0  # 原本是 0.5
        self.lambda_sobel = 1.0 # 原本是 0.5
        
        # Sobel filters
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        
        self.register_buffer('sobel_x', sobel_x)
        self.register_buffer('sobel_y', sobel_y)
        self.l1_loss = nn.L1Loss()

    def sobel_edge_loss(self, pred, target):
        pred_x = F.conv2d(pred, self.sobel_x, padding=1)
        pred_y = F.conv2d(pred, self.sobel_y, padding=1)
        
        target_x = F.conv2d(target, self.sobel_x, padding=1)
        target_y = F.conv2d(target, self.sobel_y, padding=1)
        
        pred_mag = torch.sqrt(pred_x**2 + pred_y**2 + 1e-6)
        target_mag = torch.sqrt(target_x**2 + target_y**2 + 1e-6)
        
        return self.l1_loss(pred_mag, target_mag)

    def forward(self, pred, target):
        loss_l1 = self.l1_loss(pred, target)
        # SSIM is a similarity metric (1 is best), so loss is (1 - SSIM)
        loss_ssim = 1 - ssim(pred, target)
        loss_sobel = self.sobel_edge_loss(pred, target)
        
        total_loss = self.lambda_l1 * loss_l1 + self.lambda_ssim * loss_ssim + self.lambda_sobel * loss_sobel
        return total_loss, loss_l1, loss_ssim, loss_sobel

if __name__ == "__main__":
    criterion = CompositeLoss()
    pred = torch.rand(2, 1, 512, 512)
    target = torch.rand(2, 1, 512, 512)
    loss, l1, s_loss, sob_loss = criterion(pred, target)
    print(f"Total: {loss.item():.4f}, L1: {l1.item():.4f}, SSIM: {s_loss.item():.4f}, Sobel: {sob_loss.item():.4f}")
