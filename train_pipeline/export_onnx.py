import torch
import os
from model import MobileNetV3UNet
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType

def export_to_onnx(pytorch_model_path, onnx_model_path, quantized_model_path):
    device = torch.device('cpu')
    model = MobileNetV3UNet()
    
    # 如果有訓練好的權重則載入，否則使用隨機初始化的權重進行示範
    if os.path.exists(pytorch_model_path):
        model.load_state_dict(torch.load(pytorch_model_path, map_location=device))
        print(f"Loaded weights from {pytorch_model_path}")
    else:
        print(f"Warning: {pytorch_model_path} not found. Exporting model with random weights for demonstration.")
        
    model.to(device)
    model.eval()
    
    # 建立虛擬輸入 (Batch Size 1, Channel 1, 512x512)
    dummy_input = torch.randn(1, 1, 512, 512, device=device)
    
    # 匯出 ONNX
    print(f"Exporting FP32 model to {onnx_model_path}...")
    torch.onnx.export(
        model, 
        dummy_input, 
        onnx_model_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size', 2: 'height', 3: 'width'},
                      'output': {0: 'batch_size', 2: 'height', 3: 'width'}}
    )
    print("FP32 export complete.")
    
    # 檢查是否安裝 onnxruntime 以進行量化
    try:
        print(f"Quantizing model to INT8: {quantized_model_path}...")
        quantize_dynamic(
            model_input=onnx_model_path,
            model_output=quantized_model_path,
            weight_type=QuantType.QUInt8
        )
        print("Quantization complete.")
        
        # 顯示檔案大小比較
        fp32_size = os.path.getsize(onnx_model_path) / (1024 * 1024)
        int8_size = os.path.getsize(quantized_model_path) / (1024 * 1024)
        print(f"FP32 Model Size: {fp32_size:.2f} MB")
        print(f"INT8 Model Size: {int8_size:.2f} MB")
        
    except Exception as e:
        print(f"Quantization failed. Make sure onnxruntime is installed: {e}")

if __name__ == "__main__":
    export_to_onnx(
        pytorch_model_path="checkpoints/model_epoch_126.pth",
        onnx_model_path="../web_app/model_fp32.onnx",
        quantized_model_path="../web_app/model_quantized.onnx"
    )
