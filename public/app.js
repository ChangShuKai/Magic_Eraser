const inputCanvas = document.getElementById('inputCanvas');
const outputCanvas = document.getElementById('outputCanvas');
const inputCtx = inputCanvas.getContext('2d');
const outputCtx = outputCanvas.getContext('2d');
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const processBtn = document.getElementById('processBtn');
const downloadBtn = document.getElementById('downloadBtn');
const statusText = document.getElementById('status');
const progressBarContainer = document.getElementById('progressBarContainer');

let originalFile = null;

// 1. 處理檔案上傳
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) loadImage(file);
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.background = '#e1f0fa';
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.style.background = '#f0f8ff';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.background = '#f0f8ff';
    const file = e.dataTransfer.files[0];
    if (file) loadImage(file);
});

function loadImage(file) {
    if (!file.type.match('image.*')) {
        alert("請上傳圖片檔案");
        return;
    }
    
    originalFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            // 設定 Canvas 大小
            inputCanvas.width = img.width;
            inputCanvas.height = img.height;
            outputCanvas.width = img.width;
            outputCanvas.height = img.height;
            
            // 繪製原圖
            inputCtx.drawImage(img, 0, 0);
            
            // 清空 Output
            outputCtx.clearRect(0, 0, outputCanvas.width, outputCanvas.height);
            downloadBtn.style.display = 'none';
            
            processBtn.disabled = false;
            statusText.innerText = `圖片已載入 (${img.width}x${img.height})，點擊按鈕開始處理`;
            statusText.style.color = "#3498db";
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

// 2. 送出至後端處理
processBtn.addEventListener('click', async () => {
    if (!originalFile) return;
    
    processBtn.disabled = true;
    fileInput.disabled = true;
    progressBarContainer.style.display = 'block';
    
    statusText.innerText = "正在傳送至後端進行處理...";
    statusText.style.color = "#e67e22";
    downloadBtn.style.display = 'none';
    
    // 取得設定
    const colorType = document.querySelector('input[name="color_type"]:checked').value;
    const useInpaint = document.getElementById('cb_inpaint').checked;
    const enhance = document.getElementById('cb_enhance').checked;
    
    const formData = new FormData();
    formData.append('image', originalFile);
    formData.append('color_type', colorType);
    formData.append('fill_method', useInpaint ? 'inpaint' : 'white');
    formData.append('enhance', enhance ? 'true' : 'false');
    
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP 錯誤 ${response.status}`);
        }
        
        // 取得回傳的圖片 blob
        const blob = await response.blob();
        const imgUrl = URL.createObjectURL(blob);
        
        const resultImg = new Image();
        resultImg.onload = () => {
            outputCtx.clearRect(0, 0, outputCanvas.width, outputCanvas.height);
            outputCtx.drawImage(resultImg, 0, 0);
            
            statusText.innerText = "處理完成！";
            statusText.style.color = "#2ecc71";
            downloadBtn.style.display = 'inline-block';
            
            // 讓下載按鈕記錄這個 URL
            downloadBtn.onclick = () => {
                const link = document.createElement('a');
                link.download = 'magic_eraser_output.png';
                link.href = imgUrl;
                link.click();
            };
        };
        resultImg.src = imgUrl;
        
    } catch (error) {
        console.error(error);
        statusText.innerText = `處理失敗: ${error.message}`;
        statusText.style.color = "#e74c3c";
        // 清空 Output 避免殘留
        outputCtx.clearRect(0, 0, outputCanvas.width, outputCanvas.height);
    } finally {
        processBtn.disabled = false;
        fileInput.disabled = false;
        progressBarContainer.style.display = 'none';
    }
});
