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
const loginForm = document.getElementById('loginForm');
const smsLoginForm = document.getElementById('smsLoginForm');
const registerForm = document.getElementById('registerForm');
const verifyEmailScreen = document.getElementById('verifyEmailScreen');
const loginEmail = document.getElementById('loginEmail');
const loginPassword = document.getElementById('loginPassword');
const registerEmail = document.getElementById('registerEmail');
const registerPassword = document.getElementById('registerPassword');
const registerSubmitBtn = document.getElementById('registerSubmitBtn');
const authSwitchText = document.getElementById('authSwitchText');
const authSwitchLink = document.getElementById('authSwitchLink');
const authError = document.getElementById('authError');
const googleSignInBtn = document.getElementById('googleSignInBtn');
const authDivider = document.getElementById('authDivider');

// SMS Login elements
const loginPhoneCode = document.getElementById('loginPhoneCode');
const loginPhone = document.getElementById('loginPhone');
const loginOtp = document.getElementById('loginOtp');
const otpGroup = document.getElementById('otpGroup');
const sendOtpBtn = document.getElementById('sendOtpBtn');
const smsLoginSubmitBtn = document.getElementById('smsLoginSubmitBtn');
const switchToSmsBtn = document.getElementById('switchToSmsBtn');
const switchToEmailLoginBtn = document.getElementById('switchToEmailLoginBtn');

let isLoginMode = true;
let isSmsMode = false;
let isGoogleCompleteReg = false;
let isUserVIP = false;

// Populate Birthday
function populateBirthday() {
    const yearSelect = document.getElementById('regYear');
    const monthSelect = document.getElementById('regMonth');
    const daySelect = document.getElementById('regDay');

    const currentYear = new Date().getFullYear();
    for (let i = currentYear; i >= 1930; i--) yearSelect.add(new Option(i, i));
    for (let i = 1; i <= 12; i++) monthSelect.add(new Option(i, i));
    for (let i = 1; i <= 31; i++) daySelect.add(new Option(i, i));
}
populateBirthday();

// Phone Validation for registration
const regPhone = document.getElementById('regPhone');
const phoneError = document.getElementById('phoneError');
function validatePhone() {
    const val = regPhone.value.trim();
    const regex = /^(09\d{8}|9\d{8})$/;;
    if (!regex.test(val)) {
        phoneError.style.display = 'block';
        return false;
    } else {
        phoneError.style.display = 'none';
        return true;
    }
}
regPhone.addEventListener('input', () => {
    if (regPhone.value.length > 0) validatePhone();
    else phoneError.style.display = 'none';
});

// Initialize Auth State
async function checkUser() {
    if (!supabaseClient) return;
    try {
        const { data: { user } } = await supabaseClient.auth.getUser();
        if (user) {
            // Check if registered
            if (user.user_metadata && user.user_metadata.is_registered) {
                updateAuthUI(user);
            } else {
                // Not registered fully, force registration modal
                isGoogleCompleteReg = true;
                openAuthModal('register');
                registerEmail.value = user.email;
                registerEmail.disabled = true; // prevent changing google email
            }
        } else {
            updateAuthUI(null);
        }
    } catch (e) {
        console.error(e);
    }
}

// Listen for auth events
if (supabaseClient) {
    supabaseClient.auth.onAuthStateChange((event, session) => {
        if (session && session.user) {
            if (session.user.user_metadata && session.user.user_metadata.is_registered) {
                updateAuthUI(session.user);
                authModal.style.display = 'none';
            } else {
                // Incomplete Google registration
                updateAuthUI(null);
                isGoogleCompleteReg = true;
                openAuthModal('register');
                registerEmail.value = session.user.email || '';
                registerEmail.disabled = !!session.user.email;
            }
            if (window.location.hash.includes('access_token')) {
                window.history.replaceState(null, '', window.location.pathname + window.location.search);
            }
        } else {
            updateAuthUI(null);
        }
    });
}

let currentUserId = null;
async function updateAuthUI(user) {
    if (user) {
        currentUserId = user.id;
        loginBtn.style.display = 'none';
        registerBtn.style.display = 'none';
        userInfo.style.display = 'flex';
        // prefer phone if no email
        userEmail.innerText = user.email || user.phone || '使用者';

        // Check VIP status
        try {
            const { data, error } = await supabaseClient
                .from('profiles')
                .select('is_vip')
                .eq('id', user.id)
                .single();
                
            if (currentUserId === user.id) {
                isUserVIP = (!error && data) ? !!data.is_vip : false;
                document.getElementById('vipPill').style.display = isUserVIP ? 'inline-block' : 'none';
                
                const planText = document.getElementById('currentPlanText');
                const subBtn = document.getElementById('subscribeBtn');
                const limitText = document.getElementById('limitText');
                if (planText) {
                    planText.innerText = isUserVIP ? "目前方案: SVIP" : "目前方案: 免費方案";
                }
                if (subBtn) {
                    subBtn.style.display = 'inline-block';
                }
                if (limitText) {
                    limitText.innerText = isUserVIP ? "SVIP 無限制上傳張數" : "一次最多支援上傳 3 張圖片";
                }
            }
        } catch (err) {
            console.error('Error fetching VIP status:', err);
            if (currentUserId === user.id) {
                isUserVIP = false;
                document.getElementById('vipPill').style.display = 'none';
                const planText = document.getElementById('currentPlanText');
                const subBtn = document.getElementById('subscribeBtn');
                const limitText = document.getElementById('limitText');
                if (planText) planText.innerText = "目前方案: 免費方案";
                if (subBtn) subBtn.style.display = 'inline-block';
                if (limitText) limitText.innerText = "一次最多支援上傳 3 張圖片";
            }
        }
    } else {
        currentUserId = null;
        loginBtn.style.display = 'inline-block';
        registerBtn.style.display = 'inline-block';
        userInfo.style.display = 'none';
        userEmail.innerText = '';
        isUserVIP = false;
        document.getElementById('vipPill').style.display = 'none';
        const limitText = document.getElementById('limitText');
        if (limitText) limitText.innerText = "一次最多支援上傳 3 張圖片";
    }
}

// Modal Toggle
function openAuthModal(mode) {
    isLoginMode = mode === 'login';
    isSmsMode = false;
    authTitle.innerText = isLoginMode ? '登入' : (isGoogleCompleteReg ? '完成註冊' : '註冊');

    loginForm.style.display = isLoginMode ? 'flex' : 'none';
    smsLoginForm.style.display = 'none';
    registerForm.style.display = isLoginMode ? 'none' : 'flex';
    verifyEmailScreen.style.display = 'none';

    authDivider.style.display = isGoogleCompleteReg ? 'none' : 'flex';
    googleSignInBtn.style.display = isGoogleCompleteReg ? 'none' : 'flex';
    document.querySelector('.auth-switch').style.display = isGoogleCompleteReg ? 'none' : 'block';

    authSwitchText.innerText = isLoginMode ? '還沒有帳號？ ' : '已經有帳號？ ';
    authSwitchLink.innerText = isLoginMode ? '註冊' : '登入';
    authError.style.display = 'none';

    // Reset SMS forms
    otpGroup.style.display = 'none';
    sendOtpBtn.style.display = 'block';
    smsLoginSubmitBtn.style.display = 'none';
    loginOtp.value = '';

    if (!isGoogleCompleteReg) {
        loginForm.reset();
        registerForm.reset();
        smsLoginForm.reset();
        registerEmail.disabled = false;
    }
    phoneError.style.display = 'none';
    authModal.style.display = 'flex';
}

function closeAuthModal() {
    if (isGoogleCompleteReg) {
        // If they close while pending registration, sign them out
        supabaseClient.auth.signOut();
        isGoogleCompleteReg = false;
    }
    authModal.style.display = 'none';
}

// Switching Login Modes
switchToSmsBtn.addEventListener('click', (e) => {
    e.preventDefault();
    isSmsMode = true;
    loginForm.style.display = 'none';
    smsLoginForm.style.display = 'flex';
    authTitle.innerText = '手機簡訊登入';
});

switchToEmailLoginBtn.addEventListener('click', (e) => {
    e.preventDefault();
    isSmsMode = false;
    smsLoginForm.style.display = 'none';
    loginForm.style.display = 'flex';
    authTitle.innerText = '登入';
});

// Google Sign-In
googleSignInBtn.addEventListener('click', async () => {
    if (!supabaseClient) return alert("Supabase 無法載入！");
    const { data, error } = await supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.href }
    });
    if (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
    }
});

loginBtn.addEventListener('click', () => { isGoogleCompleteReg = false; openAuthModal('login'); });
registerBtn.addEventListener('click', () => { isGoogleCompleteReg = false; openAuthModal('register'); });
closeModalBtn.addEventListener('click', closeAuthModal);
window.addEventListener('click', (e) => {
    if (e.target === authModal) closeAuthModal();
});

authSwitchLink.addEventListener('click', (e) => {
    e.preventDefault();
    openAuthModal(isLoginMode ? 'register' : 'login');
});

// Handle Login Submit (Email)
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supabaseClient) return alert("Supabase 無法載入！");
    authError.style.display = 'none';
    const btn = loginForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerText = '請稍候...';

    try {
        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email: loginEmail.value,
            password: loginPassword.value
        });
        if (error) {
            if (error.message.includes('Email not confirmed')) {
                throw new Error("信箱尚未驗證，請前往信箱點擊驗證連結。");
            }
            throw error;
        }

        // If user is not fully registered yet
        if (data.user && data.user.user_metadata && !data.user.user_metadata.is_registered) {
            isGoogleCompleteReg = true;
            openAuthModal('register');
            registerEmail.value = data.user.email;
            registerEmail.disabled = true;
        } else {
            closeAuthModal();
            checkUser();
        }
    } catch (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.innerText = '登入';
    }
});

// Handle SMS OTP Sending
sendOtpBtn.addEventListener('click', async () => {
    if (!loginPhone.value) return alert('請輸入手機號碼');
    if (!supabaseClient) return alert("Supabase 無法載入！");
    authError.style.display = 'none';

    sendOtpBtn.disabled = true;
    sendOtpBtn.innerText = '發送中...';

    const phone = `${loginPhoneCode.value}${loginPhone.value.replace(/^0/, '')}`; // format TW properly

    try {
        const { data, error } = await supabaseClient.auth.signInWithOtp({ phone });
        if (error) throw error;

        otpGroup.style.display = 'flex';
        sendOtpBtn.style.display = 'none';
        smsLoginSubmitBtn.style.display = 'block';
        alert("驗證碼已發送！");
    } catch (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
        sendOtpBtn.disabled = false;
        sendOtpBtn.innerText = '發送驗證碼';
    }
});

// Handle SMS Login Submit
smsLoginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!supabaseClient) return;
    authError.style.display = 'none';

    smsLoginSubmitBtn.disabled = true;
    smsLoginSubmitBtn.innerText = '驗證中...';

    const phone = `${loginPhoneCode.value}${loginPhone.value.replace(/^0/, '')}`;
    const token = loginOtp.value;

    try {
        const { data, error } = await supabaseClient.auth.verifyOtp({ phone, token, type: 'sms' });
        if (error) throw error;

        if (data.user && data.user.user_metadata && !data.user.user_metadata.is_registered) {
            isGoogleCompleteReg = true;
            openAuthModal('register');
        } else {
            closeAuthModal();
            checkUser();
        }
    } catch (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
        smsLoginSubmitBtn.disabled = false;
        smsLoginSubmitBtn.innerText = '驗證並登入';
    }
});

// Handle Register Submit
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validatePhone()) return;
    if (!supabaseClient) return alert("Supabase 無法載入！");

    authError.style.display = 'none';
    registerSubmitBtn.disabled = true;
    registerSubmitBtn.innerText = '請稍候...';

    const email = registerEmail.value;
    const password = registerPassword.value;
    const metadata = {
        is_registered: true,
        birthday: `${document.getElementById('regYear').value}-${document.getElementById('regMonth').value}-${document.getElementById('regDay').value}`,
        gender: document.getElementById('regGender').value,
        phone: `${document.getElementById('regPhoneCode').value} ${document.getElementById('regPhone').value}`,
        source: document.getElementById('regSource').value
    };

    try {
        if (isGoogleCompleteReg) {
            // Update existing Google user with password and metadata
            const { data, error } = await supabaseClient.auth.updateUser({
                password: password,
                data: metadata
            });
            if (error) throw error;
            alert("註冊完成！");
            isGoogleCompleteReg = false;
            closeAuthModal();
            checkUser();
        } else {
            // Normal signup - Send verification email
            const { data, error } = await supabaseClient.auth.signUp({
                email,
                password,
                options: { data: metadata }
            });
            if (error) throw error;
            if (data.user && data.user.identities && data.user.identities.length === 0) {
                throw new Error("此信箱已被註冊");
            }

            // Show verification screen
            registerForm.style.display = 'none';
            authTitle.innerText = '驗證信箱';
            document.getElementById('verifyEmailTarget').innerText = email;
            verifyEmailScreen.style.display = 'block';
            authDivider.style.display = 'none';
            googleSignInBtn.style.display = 'none';
            document.querySelector('.auth-switch').style.display = 'none';
        }
    } catch (error) {
        authError.innerText = error.message;
        authError.style.display = 'block';
    } finally {
        registerSubmitBtn.disabled = false;
        registerSubmitBtn.innerText = '註冊';
    }
});

// Resend Email button
document.getElementById('resendEmailBtn').addEventListener('click', async () => {
    const email = document.getElementById('verifyEmailTarget').innerText;
    try {
        const { error } = await supabaseClient.auth.resend({ type: 'signup', email });
        if (error) throw error;
        alert('驗證信已重新發送！');
    } catch (error) {
        alert('發送失敗：' + error.message);
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
const MAX_FILES = 3;

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

    const limit = isUserVIP ? Infinity : MAX_FILES;
    if (validFiles.length > limit) {
        alert(`一般會員最多只能上傳 ${MAX_FILES} 張圖片，將只取前 ${MAX_FILES} 張。\n升級 SVIP 即可無限制上傳！`);
        validFiles.splice(limit);
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
            // TODO: 等到 Cloud Run 部署完成後，將下方的 URL 替換為您的 Cloud Run 服務網址 (例如：https://your-cloud-run-url.a.run.app/api/index)
            const API_URL = 'https://changshukai--exam-cleaner-cleanerservice-clean-image.modal.run';
            
            const response = await fetch(API_URL, {
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

// 4. VIP Feature Enforcement
document.getElementById('cb_inpaint').addEventListener('click', (e) => {
    if (!isUserVIP) {
        e.preventDefault();
        alert("✨ 使用 AI 智慧修補 (Inpaint) 是 SVIP 專屬功能！請升級 SVIP 後使用。");
    }
});

document.getElementById('cb_enhance').addEventListener('click', (e) => {
    if (!isUserVIP) {
        e.preventDefault();
        alert("🌓 增強黑白對比度 是 SVIP 專屬功能！請升級 SVIP 後使用。");
    }
});
