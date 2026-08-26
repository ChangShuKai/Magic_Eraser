// --- Supabase Setup ---
const SUPABASE_URL = 'https://qrjkjdlwhmihxkqnrxzu.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFyamtqZGx3aG1paHhrcW5yeHp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc1NDYzMjYsImV4cCI6MjEwMzEyMjMyNn0.Z4VAfv6SIUvibLv5h02Arp9gq3jeCPWwBc_S1zuNUDA';
let supabaseClient = null;
try {
    if (window.supabase) {
        supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    } else {
        console.warn("Supabase CDN not loaded.");
    }
} catch (e) {
    console.error("Supabase init error:", e);
}

// Auth UI Elements
const loginBtn = document.getElementById('loginBtn');
const registerBtn = document.getElementById('registerBtn');
const userInfo = document.getElementById('userInfo');
const userEmail = document.getElementById('userEmail');
const logoutBtn = document.getElementById('logoutBtn');

const authModal = document.getElementById('authModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const authTitle = document.getElementById('authTitle');
const authForm = document.getElementById('authForm');
const emailInput = document.getElementById('emailInput');
const passwordInput = document.getElementById('passwordInput');
const authSubmitBtn = document.getElementById('authSubmitBtn');
const authSwitchText = document.getElementById('authSwitchText');
const authSwitchLink = document.getElementById('authSwitchLink');
const authError = document.getElementById('authError');
const googleSignInBtn = document.getElementById('googleSignInBtn');

let isLoginMode = true;

// Initialize Auth State
async function checkUser() {
    if (!supabaseClient) return;
    try {
        const { data: { user } } = await supabaseClient.auth.getUser();
        updateAuthUI(user);
    } catch (e) {
        console.error(e);
    }
}

// Listen for auth events (e.g. returning from Google OAuth redirect)
if (supabaseClient) {
    supabaseClient.auth.onAuthStateChange((event, session) => {
        if (session && session.user) {
            updateAuthUI(session.user);
            // Optionally remove the hash from the URL to clean it up
            if (window.location.hash.includes('access_token')) {
                window.history.replaceState(null, '', window.location.pathname + window.location.search);
            }
        } else {
            updateAuthUI(null);
        }
    });
}

function updateAuthUI(user) {
    if (user) {
        loginBtn.style.display = 'none';
        registerBtn.style.display = 'none';
        userInfo.style.display = 'flex';
        userEmail.innerText = user.email;
    } else {
        loginBtn.style.display = 'inline-block';
        registerBtn.style.display = 'inline-block';
        userInfo.style.display = 'none';
        userEmail.innerText = '';
    }
}

// Modal Toggle
function openAuthModal(mode) {
    isLoginMode = mode === 'login';
    authTitle.innerText = isLoginMode ? '登入' : '註冊';
    authSubmitBtn.innerText = isLoginMode ? '登入' : '註冊';
    authSwitchText.innerText = isLoginMode ? '還沒有帳號？ ' : '已經有帳號？ ';
    authSwitchLink.innerText = isLoginMode ? '註冊' : '登入';
    authError.style.display = 'none';
    authForm.reset();
    authModal.style.display = 'flex';
}

function closeAuthModal() {
    authModal.style.display = 'none';
}

googleSignInBtn.addEventListener('click', async () => {
    if (!supabaseClient) {
        alert("Supabase 無法載入，請重新整理或關閉廣告阻擋器！");
        return;
    }
    const { data, error } = await supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo: window.location.href, // 確保跳轉回當前網址
        }
    });
    if (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
    }
});

loginBtn.addEventListener('click', () => openAuthModal('login'));
registerBtn.addEventListener('click', () => openAuthModal('register'));
closeModalBtn.addEventListener('click', closeAuthModal);
window.addEventListener('click', (e) => {
    if (e.target === authModal) closeAuthModal();
});

authSwitchLink.addEventListener('click', (e) => {
    e.preventDefault();
    openAuthModal(isLoginMode ? 'register' : 'login');
});

// Handle Auth Submit
authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supabaseClient) {
        alert("Supabase 無法載入，請重新整理或關閉廣告阻擋器！");
        return;
    }
    authError.style.display = 'none';
    authSubmitBtn.disabled = true;
    authSubmitBtn.innerText = '請稍候...';
    
    const email = emailInput.value;
    const password = passwordInput.value;
    
    try {
        if (isLoginMode) {
            const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
            if (error) throw error;
        } else {
            const { data, error } = await supabaseClient.auth.signUp({ email, password });
            if (error) throw error;
            if (data.user && data.user.identities && data.user.identities.length === 0) {
                throw new Error("此信箱已被註冊");
            }
            alert("註冊成功！如果需要驗證信，請前往信箱確認。");
        }
        closeAuthModal();
        checkUser();
    } catch (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
    } finally {
        authSubmitBtn.disabled = false;
        authSubmitBtn.innerText = isLoginMode ? '登入' : '註冊';
    }
});

// Logout
logoutBtn.addEventListener('click', async () => {
    if (supabaseClient) {
        await supabaseClient.auth.signOut();
    }
    checkUser();
});

// Call on load
checkUser();

const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const processBtn = document.getElementById('processBtn');
const downloadAllBtn = document.getElementById('downloadAllBtn');
const statusText = document.getElementById('status');
const progressBarContainer = document.getElementById('progressBarContainer');
const progressBar = document.getElementById('progressBar');
const previewGallery = document.getElementById('previewGallery');
const fileCountSpan = document.getElementById('fileCount');

let selectedFiles = []; // Array of objects: { id, file, resultUrl, status }
const MAX_FILES = 10;

// 1. 處理檔案上傳
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary)';
    dropZone.style.background = '#eff6ff';
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#cbd5e1';
    dropZone.style.background = '#f8fafc';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#cbd5e1';
    dropZone.style.background = '#f8fafc';
    handleFiles(e.dataTransfer.files);
});

function handleFiles(files) {
    const validFiles = Array.from(files).filter(f => f.type.match('image.*'));
    
    if (validFiles.length === 0) {
        alert("請上傳圖片檔案 (JPG, PNG)");
        return;
    }

    if (validFiles.length > MAX_FILES) {
        alert(`最多只能上傳 ${MAX_FILES} 張圖片，將只取前 ${MAX_FILES} 張。`);
        validFiles.splice(MAX_FILES);
    }
    
    // 清空舊的
    selectedFiles = [];
    previewGallery.innerHTML = '';
    downloadAllBtn.style.display = 'none';

    validFiles.forEach((file, index) => {
        const fileObj = {
            id: `file_${index}`,
            file: file,
            resultUrl: null,
            status: 'pending' // pending, processing, done, error
        };
        selectedFiles.push(fileObj);
        createPreviewCard(fileObj);
    });

    fileCountSpan.innerText = selectedFiles.length;
    processBtn.disabled = false;
    statusText.innerText = `已載入 ${selectedFiles.length} 張圖片，點擊按鈕開始處理`;
    statusText.style.color = "var(--primary)";
    
    // reset input value so you can select the same files again
    fileInput.value = '';
}

function createPreviewCard(fileObj) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const cardHTML = `
            <div class="image-card" id="card_${fileObj.id}">
                <div class="card-header">
                    <div class="file-name">${fileObj.file.name}</div>
                    <div class="file-status status-pending" id="status_${fileObj.id}">等待處理</div>
                </div>
                <div class="preview-box">
                    <h4><span>原始圖片</span> <span class="badge">Input</span></h4>
                    <div class="canvas-wrapper">
                        <canvas id="input_${fileObj.id}"></canvas>
                    </div>
                </div>
                <div class="preview-box">
                    <h4>
                        <span>處理結果</span> 
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <button class="download-btn-small" id="dl_${fileObj.id}">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                                儲存
                            </button>
                            <span class="badge badge-output">Output</span>
                        </div>
                    </h4>
                    <div class="canvas-wrapper">
                        <canvas id="output_${fileObj.id}"></canvas>
                    </div>
                </div>
            </div>
        `;
        
        // Append to gallery
        previewGallery.insertAdjacentHTML('beforeend', cardHTML);
        
        // Draw input image
        const img = new Image();
        img.onload = () => {
            const canvas = document.getElementById(`input_${fileObj.id}`);
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(fileObj.file);
}

// 2. 送出至後端處理
processBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;
    
    processBtn.disabled = true;
    fileInput.disabled = true;
    downloadAllBtn.style.display = 'none';
    progressBarContainer.style.display = 'block';
    
    statusText.innerText = "正在傳送至後端進行處理...";
    statusText.style.color = "#e67e22";
    
    // 取得設定
    const colorType = document.querySelector('input[name="color_type"]:checked').value;
    const useInpaint = document.getElementById('cb_inpaint').checked;
    const enhance = document.getElementById('cb_enhance').checked;
    
    let completedCount = 0;
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const fileObj = selectedFiles[i];
        
        // Update UI for processing
        const statusEl = document.getElementById(`status_${fileObj.id}`);
        statusEl.className = 'file-status status-processing';
        statusEl.innerText = '處理中...';
        
        // Update global progress
        const percent = (i / selectedFiles.length) * 100;
        progressBar.style.width = `${percent}%`;
        progressBar.classList.remove('progress-indeterminate');
        
        const formData = new FormData();
        formData.append('image', fileObj.file);
        formData.append('color_type', colorType);
        formData.append('fill_method', useInpaint ? 'inpaint' : 'white');
        formData.append('enhance', enhance ? 'true' : 'false');
        
        try {
            const response = await fetch('https://changshukai--exam-cleaner-cleanerservice-clean-image.modal.run', {
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
            fileObj.resultUrl = imgUrl;
            
            // Draw output image
            await new Promise((resolve) => {
                const resultImg = new Image();
                resultImg.onload = () => {
                    const canvas = document.getElementById(`output_${fileObj.id}`);
                    const ctx = canvas.getContext('2d');
                    canvas.width = resultImg.width;
                    canvas.height = resultImg.height;
                    ctx.drawImage(resultImg, 0, 0);
                    
                    // Setup single download button
                    const dlBtn = document.getElementById(`dl_${fileObj.id}`);
                    dlBtn.style.display = 'inline-flex';
                    dlBtn.onclick = () => {
                        const link = document.createElement('a');
                        link.download = `erased_${fileObj.file.name}`;
                        link.href = imgUrl;
                        link.click();
                    };
                    
                    resolve();
                };
                resultImg.src = imgUrl;
            });
            
            statusEl.className = 'file-status status-done';
            statusEl.innerText = '處理完成';
            completedCount++;
            
        } catch (error) {
            console.error(error);
            statusEl.className = 'file-status status-error';
            statusEl.innerText = '處理失敗';
            fileObj.status = 'error';
        }
    }
    
    // Done
    progressBar.style.width = `100%`;
    processBtn.disabled = false;
    fileInput.disabled = false;
    
    if (completedCount > 0) {
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
    }, 2000);
});

// 3. 一鍵下載全部 (ZIP)
downloadAllBtn.addEventListener('click', async () => {
    if (typeof JSZip === 'undefined') {
        alert("無法載入 JSZip，請使用單張下載。");
        return;
    }
    
    const zip = new JSZip();
    let hasFiles = false;
    
    downloadAllBtn.disabled = true;
    const oldText = downloadAllBtn.innerHTML;
    downloadAllBtn.innerHTML = "正在打包...";
    
    const successfulFiles = selectedFiles.filter(f => f.resultUrl);
    
    for (let i = 0; i < successfulFiles.length; i++) {
        const fileObj = successfulFiles[i];
        try {
            const response = await fetch(fileObj.resultUrl);
            const blob = await response.blob();
            zip.file(`erased_${fileObj.file.name}`, blob);
            hasFiles = true;
        } catch (e) {
            console.error("Error zipping file:", e);
        }
    }
    
    if (hasFiles) {
        const content = await zip.generateAsync({ type: "blob" });
        const link = document.createElement('a');
        link.download = "MagicEraser_Results.zip";
        link.href = URL.createObjectURL(content);
        link.click();
    }
    
    downloadAllBtn.innerHTML = oldText;
    downloadAllBtn.disabled = false;
});
