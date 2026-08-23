import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

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
        # e1: 1/2 resolution (256x256), 16 channels
        self.enc1 = nn.Sequential(self.conv1, backbone[0][1], backbone[0][2])
        
        # e2: 1/4 resolution (128x128), 16 channels
        self.enc2 = backbone[1]
        
        # e3: 1/8 resolution (64x64), 24 channels
        self.enc3 = nn.Sequential(backbone[2], backbone[3])
        
        # e4: 1/16 resolution (32x32), 48 channels
        self.enc4 = nn.Sequential(backbone[4], backbone[5], backbone[6], backbone[7], backbone[8])
        
        # e5: 1/32 resolution (16x16), 96 channels
        self.enc5 = nn.Sequential(backbone[9], backbone[10], backbone[11])
        
        # Decoder parts with Skip Connections
        # Input to dec4: enc5 output (96)
        self.up4 = nn.ConvTranspose2d(96, 48, kernel_size=2, stride=2)
        self.dec4 = nn.Sequential(
            nn.Conv2d(48 + 48, 48, kernel_size=3, padding=1),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )

        # Input to dec3: dec4 output (48) + enc3 output (24)
        self.up3 = nn.ConvTranspose2d(48, 24, kernel_size=2, stride=2)
        self.dec3 = nn.Sequential(
            nn.Conv2d(24 + 24, 24, kernel_size=3, padding=1),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True)
        )
        
        # Input to dec2: dec3 output (24) + enc2 output (16)
        self.up2 = nn.ConvTranspose2d(24, 16, kernel_size=2, stride=2)
        self.dec2 = nn.Sequential(
            nn.Conv2d(16 + 16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True)
        )
        
        # Input to dec1: dec2 output (16) + enc1 output (16)
        self.up1 = nn.ConvTranspose2d(16, 16, kernel_size=2, stride=2)
        self.dec1 = nn.Sequential(
            nn.Conv2d(16 + 16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True)
        )
        
        # Final upsampling to original resolution (1/2 -> 1)
        self.up0 = nn.ConvTranspose2d(16, 16, kernel_size=2, stride=2)
        
        # Output layer
        self.out_conv = nn.Sequential(
            nn.Conv2d(16, 1, kernel_size=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        e1 = self.enc1(x)   # (B, 16, 256, 256)
        e2 = self.enc2(e1)  # (B, 16, 128, 128)
        e3 = self.enc3(e2)  # (B, 24, 64, 64)
        e4 = self.enc4(e3)  # (B, 48, 32, 32)
        e5 = self.enc5(e4)  # (B, 96, 16, 16)
        
        d4 = self.up4(e5)                   # (B, 48, 32, 32)
        d4 = torch.cat([d4, e4], dim=1)     # (B, 96, 32, 32)
        d4 = self.dec4(d4)                  # (B, 48, 32, 32)

        d3 = self.up3(d4)                   # (B, 24, 64, 64)
        d3 = torch.cat([d3, e3], dim=1)     # (B, 48, 64, 64)
        d3 = self.dec3(d3)                  # (B, 24, 64, 64)
        
        d2 = self.up2(d3)                   # (B, 16, 128, 128)
        d2 = torch.cat([d2, e2], dim=1)     # (B, 32, 128, 128)
        d2 = self.dec2(d2)                  # (B, 16, 128, 128)
        
        d1 = self.up1(d2)                   # (B, 16, 256, 256)
        d1 = torch.cat([d1, e1], dim=1)     # (B, 32, 256, 256)
        d1 = self.dec1(d1)                  # (B, 16, 256, 256)
        
        d0 = self.up0(d1)                   # (B, 16, 512, 512)
        out = self.out_conv(d0)             # (B, 1, 512, 512)
        
        return out

if __name__ == "__main__":
    model = MobileNetV3UNet()
    x = torch.randn(1, 1, 512, 512)
    y = model(x)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.2f} M")
    print(f"Output shape: {y.shape}")
