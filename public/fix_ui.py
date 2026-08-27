import re

# --- Update HTML ---
with open('d:/書愷/硬碟暫放/Python/去手寫/public/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Add Toast Container
if '<div id="toastContainer" class="toast-container"></div>' not in html_content:
    html_content = html_content.replace('<body>', '<body>\n    <div id="toastContainer" class="toast-container"></div>')

# Add Toast CSS and User Profile CSS
css_to_add = """
        /* Toast Notifications */
        .toast-container {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
            pointer-events: none;
        }
        .toast {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-lg);
            border-radius: var(--radius-md);
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 320px;
            max-width: 400px;
            transform: translateX(120%);
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            opacity: 0;
            pointer-events: auto;
        }
        .toast.show {
            transform: translateX(0);
            opacity: 1;
        }
        .toast.hide {
            transform: translateX(120%);
            opacity: 0;
        }
        .toast-icon {
            font-size: 1.3rem;
            flex-shrink: 0;
        }
        .toast-content {
            flex-grow: 1;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-main);
            line-height: 1.4;
        }
        
        /* User Profile Enhancements */
        .user-profile-container {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .user-profile-pill {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid var(--border-color);
            padding: 6px 16px 6px 6px;
            border-radius: 40px;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
        }
        .user-profile-pill:hover {
            box-shadow: var(--shadow-md);
            background: #ffffff;
        }
        .user-avatar {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--text-main), #4b5563);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        .user-details {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .user-email {
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--text-main);
            line-height: 1;
            margin-bottom: 2px;
        }
        .user-plan-text {
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--text-muted);
            line-height: 1;
        }
        .icon-btn {
            padding: 10px;
            border-radius: 50%;
            background: #ffffff;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            box-shadow: var(--shadow-sm);
        }
        .icon-btn:hover {
            color: var(--danger);
            border-color: #fca5a5;
            background: #fef2f2;
        }
    </style>"""

if '.toast-container {' not in html_content:
    html_content = html_content.replace('</style>', css_to_add)

# Replace old userInfo HTML
old_user_info = r'<div id="userInfo"[^>]*>.*?</div>\s*</div>\s*</nav>'
new_user_info = """
            <div id="userInfo" class="user-profile-container" style="display: none;">
                <button type="button" id="subscribeBtn" class="auth-btn vip-btn" style="display: none;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                    升級 SVIP
                </button>
                <div class="user-profile-pill">
                    <div class="user-avatar">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                    </div>
                    <div class="user-details">
                        <span id="userEmail" class="user-email"></span>
                        <span id="currentPlanText" class="user-plan-text">免費方案</span>
                    </div>
                    <span id="vipPill" class="vip-badge" style="display: none; margin-left: 4px;">SVIP</span>
                </div>
                <button class="auth-btn icon-btn" id="logoutBtn" title="登出">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                </button>
            </div>
        </div>
    </nav>
"""
html_content = re.sub(old_user_info, new_user_info, html_content, flags=re.DOTALL)

with open('d:/書愷/硬碟暫放/Python/去手寫/public/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# --- Update JS ---
with open('d:/書愷/硬碟暫放/Python/去手寫/public/app.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Replace alert(...) with window.showToast(...) or window.alert which is overridden
# Let's override window.alert at the top of app.js
toast_js = """
// Toast Notification System
window.showToast = function(msg, type='info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    let icon = '✨';
    if(type === 'success') icon = '✅';
    if(type === 'error') icon = '❌';
    if(type === 'warning') icon = '⚠️';
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">${msg}</div>
    `;
    container.appendChild(toast);
    
    // trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
};

window.alert = function(msg) {
    let type = 'info';
    if (typeof msg === 'string') {
        if (msg.includes('失敗') || msg.includes('無法') || msg.includes('請輸入') || msg.includes('錯誤') || msg.includes('只能')) type = 'error';
        if (msg.includes('SVIP') && !msg.includes('失敗')) type = 'warning';
        if (msg.includes('完成') || msg.includes('成功') || msg.includes('已發送')) type = 'success';
    }
    showToast(msg, type);
};

"""
if 'window.showToast = function' not in js_content:
    js_content = toast_js + js_content

# Fix subscribeBtn logic
js_content = js_content.replace(
    "subBtn.style.display = 'inline-block';",
    "subBtn.style.display = isUserVIP ? 'none' : 'inline-flex';"
)

with open('d:/書愷/硬碟暫放/Python/去手寫/public/app.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print("UI/UX and JS updated successfully.")
