import re

with open('public/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add DOM elements for the steps
dom_insert = """
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const goToStep2Btn = document.getElementById('goToStep2Btn');
const backToStep1Btn = document.getElementById('backToStep1Btn');
const step1Actions = document.getElementById('step1Actions');

if (goToStep2Btn) {
    goToStep2Btn.addEventListener('click', () => {
        step1.style.display = 'none';
        step2.style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}
if (backToStep1Btn) {
    backToStep1Btn.addEventListener('click', () => {
        step2.style.display = 'none';
        step1.style.display = 'block';
    });
}
"""
content = content.replace("const previewGallery = document.getElementById('previewGallery');", "const previewGallery = document.getElementById('previewGallery');" + dom_insert)

# Modify handleFiles to show step1Actions
handle_files_old = """    fileCountSpan.innerText = selectedFiles.length;
    processBtn.disabled = false;
    statusText.innerText = `已載入 ${selectedFiles.length} 張圖片，點擊按鈕開始處理`;"""
    
handle_files_new = """    fileCountSpan.innerText = selectedFiles.length;
    processBtn.disabled = false;
    statusText.innerText = `已載入 ${selectedFiles.length} 張圖片，點擊按鈕開始處理`;
    if (step1Actions) {
        step1Actions.style.display = 'block';
        if (goToStep2Btn) goToStep2Btn.innerText = `下一步：設定與去除 (${selectedFiles.length} 張)`;
    }"""
content = content.replace(handle_files_old, handle_files_new)

# Modify processBtn done section
done_old = """    if (completedCount > 0) {
        statusText.innerText = `處理完畢！成功: ${completedCount}/${selectedFiles.length}`;
        statusText.style.color = "#2ecc71";
        if (completedCount > 1) {
            downloadAllBtn.style.display = 'inline-flex';
        }
    } else {
        statusText.innerText = `所有圖片處理失敗`;
        statusText.style.color = "#e74c3c";
    }

    // Hide progress bar after 2 seconds
    setTimeout(() => {
        progressBarContainer.style.display = 'none';
        progressBar.style.width = `0%`;
    }, 2000);"""

done_new = """    if (completedCount > 0) {
        statusText.innerText = `處理完畢！成功: ${completedCount}/${selectedFiles.length}`;
        statusText.style.color = "#2ecc71";
        // Always show downloadAllBtn when success
        downloadAllBtn.style.display = 'inline-flex';
        
        // Go to Step 3 after a short delay
        setTimeout(() => {
            if (step2 && step3) {
                step2.style.display = 'none';
                step3.style.display = 'block';
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }, 1500);
        
    } else {
        statusText.innerText = `所有圖片處理失敗`;
        statusText.style.color = "#e74c3c";
    }

    // Hide progress bar after 2 seconds
    setTimeout(() => {
        progressBarContainer.style.display = 'none';
        progressBar.style.width = `0%`;
    }, 2000);"""
content = content.replace(done_old, done_new)

with open('public/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated app.js")
