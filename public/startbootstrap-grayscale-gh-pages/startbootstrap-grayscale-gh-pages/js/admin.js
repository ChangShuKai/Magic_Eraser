/**
 * Admin Panel Security Handlers
 * - Uses DOMPurify for XSS protection
 * - Handles Cookie-based authentication via credentials: 'include'
 * - Implements Step-up Auth (MFA) for critical actions
 */

// 確保已載入 DOMPurify (應從 CDN 或本地載入)
if (typeof DOMPurify === 'undefined') {
    console.error('DOMPurify is not loaded! Security risk.');
}

const API_BASE = '/api/admin_server';

// 安全的 API 呼叫封裝
async function secureFetch(endpoint, options = {}) {
    // 憑證隔離：必須設定 credentials: 'include' 以攜帶 HttpOnly Cookie
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            // 避免 CSRF，可以加入自定義 Header (若後端有驗證)
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'include' 
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, mergedOptions);
        
        if (response.status === 401 || response.status === 403) {
            // 身分驗證失敗，切換到登入畫面
            showLoginView();
            throw new Error('Authentication required');
        }
        
        return response;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// 渲染管理員儀表板 (含 DOMPurify 消毒)
async function loadDashboard() {
    try {
        const response = await secureFetch('/system-status');
        if (response.ok) {
            const data = await response.json();
            
            // 全鏈路內容消毒：使用 DOMPurify 防禦 XSS
            const safeUsername = DOMPurify.sanitize(data.current_user);
            const safeRole = DOMPurify.sanitize(data.role);
            const safeStatus = DOMPurify.sanitize(data.status);
            
            document.getElementById('admin-content').innerHTML = `
                <h2 class="text-white mb-4">Welcome, ${safeUsername}</h2>
                <p class="text-white-50">Role: ${safeRole}</p>
                <p class="text-white-50">System Status: ${safeStatus}</p>
                <p class="text-white-50">Active Users: ${DOMPurify.sanitize(data.active_users.toString())}</p>
                
                <hr class="my-4" style="border-color: rgba(255,255,255,0.1);" />
                <h4 class="text-white mb-3">Critical Actions</h4>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card bg-dark text-white border-danger mb-3">
                            <div class="card-body">
                                <h5 class="card-title text-danger">Purge System Logs</h5>
                                <p class="card-text">Warning: This action cannot be undone and requires Step-up Auth.</p>
                                <button class="btn btn-outline-danger" onclick="promptStepUpAuth('purge_logs')">Execute</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            showDashboardView();
        }
    } catch (error) {
        // 已在 secureFetch 處理 401
    }
}

// 登入功能
document.getElementById('adminLoginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('adminUser').value;
    const password = document.getElementById('adminPass').value;
    const totp = document.getElementById('adminTotp').value;
    
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, totp }),
            // 必須允許寫入 Cookie
            credentials: 'include'
        });
        
        if (response.ok) {
            // 登入成功，不需要/不能將 Token 存入 localStorage
            loadDashboard();
        } else {
            const err = await response.json();
            alert('Login failed: ' + DOMPurify.sanitize(err.detail));
        }
    } catch (error) {
        alert('Network error during login');
    }
});

// 登出功能
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    await secureFetch('/logout', { method: 'POST' });
    showLoginView();
});

// 高風險操作二次驗證 (Step-up Auth)
async function promptStepUpAuth(actionId) {
    const totpCode = prompt("Enter your TOTP code from Google Authenticator to confirm this critical action:");
    if (!totpCode) return;
    
    try {
        const response = await secureFetch(`/items/${actionId}`, {
            method: 'DELETE',
            body: JSON.stringify({ item_id: actionId, totp: totpCode })
        });
        
        if (response.ok) {
            const data = await response.json();
            alert('Success: ' + DOMPurify.sanitize(data.message));
        } else {
            const err = await response.json();
            alert('Action failed: ' + DOMPurify.sanitize(err.detail));
        }
    } catch (error) {
        console.error('Critical action failed', error);
    }
}

// 視圖切換
function showLoginView() {
    document.getElementById('login-section').style.display = 'block';
    document.getElementById('dashboard-section').style.display = 'none';
}

function showDashboardView() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('dashboard-section').style.display = 'block';
}

// 初始化
window.addEventListener('DOMContentLoaded', () => {
    // 嘗試載入 Dashboard，若無 Cookie 會自動跳轉登入
    loadDashboard();
});
