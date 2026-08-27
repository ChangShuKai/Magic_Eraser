import re

with open('d:/書愷/硬碟暫放/Python/去手寫/public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace VIP Pill inline styles
content = re.sub(
    r'id="vipPill" style="[^"]+"',
    'id="vipPill" class="vip-badge" style="display: none;"',
    content
)

# Subscribe button
content = re.sub(
    r'id="subscribeBtn" class="auth-btn" style="[^"]+"',
    'id="subscribeBtn" class="auth-btn vip-btn" style="display: none;"',
    content
)

# VIP Badges
content = re.sub(
    r'class="vip-badge" style="[^"]+"',
    'class="vip-badge"',
    content
)

# Payment button
content = re.sub(
    r'class="btn" style="padding: 14px 24px; width: 100%; background: linear-gradient\(135deg, #f59e0b, #d97706\);"',
    'class="btn vip-btn" style="width: 100%;"',
    content
)

# Add .vip-btn class to styles if not exists
if '.vip-btn' not in content:
    vip_css = """
        .vip-btn {
            background: linear-gradient(135deg, #f59e0b, #d97706) !important;
            color: white !important;
            border: none;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4) !important;
        }
        .vip-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(245, 158, 11, 0.6) !important;
        }
    </style>"""
    content = content.replace('</style>', vip_css)

with open('d:/書愷/硬碟暫放/Python/去手寫/public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("HTML cleaned")
