import os

app_js_path = 'public/app.js'
with open(app_js_path, 'r', encoding='utf-8') as f:
    app_js = f.read()

# Fix event listeners that might be null
replacements = [
    ("fileInput.addEventListener('change'", "if (fileInput) fileInput.addEventListener('change'"),
    ("dropZone.addEventListener('dragover'", "if (dropZone) dropZone.addEventListener('dragover'"),
    ("dropZone.addEventListener('dragleave'", "if (dropZone) dropZone.addEventListener('dragleave'"),
    ("dropZone.addEventListener('drop'", "if (dropZone) dropZone.addEventListener('drop'"),
    ("processBtn.addEventListener('click'", "if (processBtn) processBtn.addEventListener('click'"),
    ("downloadAllBtn.addEventListener('click'", "if (downloadAllBtn) downloadAllBtn.addEventListener('click'"),
    ("document.getElementById('cb_inpaint').addEventListener('click'", "if (document.getElementById('cb_inpaint')) document.getElementById('cb_inpaint').addEventListener('click'"),
    ("document.getElementById('cb_enhance').addEventListener('click'", "if (document.getElementById('cb_enhance')) document.getElementById('cb_enhance').addEventListener('click'"),
]

for old, new in replacements:
    app_js = app_js.replace(old, new)

# Also fix radio buttons for color_type
radio_old = """document.querySelectorAll('input[name="color_type"]').forEach(radio => {
    radio.addEventListener('change', updateRadioGlider);
});"""
radio_new = """document.querySelectorAll('input[name="color_type"]').forEach(radio => {
    if (radio) radio.addEventListener('change', updateRadioGlider);
});"""
app_js = app_js.replace(radio_old, radio_new)

# Fix fileCountSpan used before definition
app_js = app_js.replace("const fileCountSpan = document.getElementById('fileCount');", "")
app_js = app_js.replace("const dropZone = document.getElementById('dropZone');", "const dropZone = document.getElementById('dropZone');\nconst fileCountSpan = document.getElementById('fileCount');")

# Also there's one more check: fileCountSpan might be null on index.html
app_js = app_js.replace("fileCountSpan.innerText = selectedFiles.length;", "if (fileCountSpan) fileCountSpan.innerText = selectedFiles.length;")

with open(app_js_path, 'w', encoding='utf-8') as f:
    f.write(app_js)
    
intro_path = 'public/introduce.html'
with open(intro_path, 'r', encoding='utf-8') as f:
    intro = f.read()

intro = intro.replace("一鍵去除雜亂背景，凸顯主體。", "一鍵去除手寫筆跡，還原乾淨考卷。")
intro = intro.replace("能以像素級別精準識別並消除圖片中不需要的元素，讓您的影像乾淨無瑕。", "能以像素級別精準識別並消除考卷上的手寫筆跡，讓您的考卷乾淨無瑕。")
intro = intro.replace("一鍵去背", "一鍵去手寫")
intro = intro.replace("令人驚嘆的去背成果", "令人驚嘆的去除筆跡成果")

with open(intro_path, 'w', encoding='utf-8') as f:
    f.write(intro)

print("Done fixing app.js and introduce.html")
