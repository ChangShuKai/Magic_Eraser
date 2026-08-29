import os
import re

js_path = r"d:\書愷\硬碟暫放\Python\去手寫\public\app.js"

with open(js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update navigateTo
new_navigate = """function navigateTo(path) {
    if (path === '/process') {
        window.location.href = 'process.html';
    } else if (path === '/download') {
        window.location.href = 'download.html';
    } else {
        window.location.href = 'index.html';
    }
}"""
content = re.sub(r'function navigateTo\(path\)\s*\{[\s\S]*?\}\n\nfunction handleRoute', new_navigate + '\n\nfunction handleRoute', content)

# 2. Update handleRoute
new_handle = """function handleRoute() {
    // Determine which page we are on
    const path = window.location.pathname;
    const isProcess = path.includes('process.html');
    const isDownload = path.includes('download.html');
    
    // Load state from localforage
    localforage.getItem('magic_eraser_files').then((savedFiles) => {
        if (savedFiles && savedFiles.length > 0) {
            selectedFiles = savedFiles;
            fileCountSpan.innerText = selectedFiles.length;
            
            if (isProcess) {
                // Populate preview gallery for process page
                previewGallery.innerHTML = '';
                selectedFiles.forEach(fileObj => {
                    createPreviewCard(fileObj);
                });
                processBtn.disabled = false;
            } else if (isDownload) {
                // Populate preview gallery for download page
                previewGallery.innerHTML = '';
                selectedFiles.forEach(fileObj => {
                    createPreviewCard(fileObj);
                });
                downloadAllBtn.style.display = 'inline-flex';
            }
        } else {
            // No files, redirect to index if not on index
            if (isProcess || isDownload) {
                window.location.href = 'index.html';
            }
        }
    }).catch((err) => {
        console.error('Error loading files:', err);
    });
}"""

content = re.sub(r'function handleRoute\(\)\s*\{[\s\S]*?window\.addEventListener\(\'hashchange\', \(\) => \{\n    if \(window\.location\.protocol === \'file:\'\) handleRoute\(\);\n\}\);', new_handle, content)

# 3. Save selectedFiles to localforage when handleFiles is called
handle_files_repl = """    fileInput.value = '';
    
    // Save to localforage
    localforage.setItem('magic_eraser_files', selectedFiles).catch(console.error);"""
content = content.replace("    fileInput.value = '';", handle_files_repl)

# 4. Save to localforage when clearing (restartBtn)
restart_repl = """        selectedFiles = [];
        localforage.setItem('magic_eraser_files', []);
        previewGallery.innerHTML = '';"""
content = content.replace("        selectedFiles = [];\n        previewGallery.innerHTML = '';", restart_repl)

# 5. Save to localforage when result is processed
# Let's find where resultUrl is set
result_repl = """                fileObj.status = 'done';
                
                // Save updated status to localforage
                localforage.setItem('magic_eraser_files', selectedFiles).catch(console.error);"""
content = content.replace("                fileObj.status = 'done';", result_repl)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("app.js refactored successfully.")
