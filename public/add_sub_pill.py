import re

html_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Add CSS for subscribe-pill-btn
css_to_add = """
        .subscribe-pill-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 40px;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
            transition: var(--transition);
        }
        .subscribe-pill-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4);
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
        }
"""
if '.subscribe-pill-btn' not in html:
    html = html.replace('/* User Profile Enhancements */', css_to_add + '\n        /* User Profile Enhancements */')

# Update the HTML for subscribeBtn
old_btn = r'<button type="button" id="subscribeBtn" class="auth-btn vip-btn" style="display: none;">.*?升級 SVIP\s*</button>'
new_btn = """<button type="button" id="subscribeBtn" class="subscribe-pill-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                    訂閱方案
                </button>"""
html = re.sub(old_btn, new_btn, html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
    
print("HTML updated for subscribe pill")
