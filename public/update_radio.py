import re

html_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Add glider element to radio-group
if '<div class="radio-glider"></div>' not in html:
    html = html.replace(
        '<div class="radio-group">',
        '<div class="radio-group" style="position: relative; z-index: 1;">\n                        <div class="radio-glider"></div>'
    )

# Update CSS for radio-group and glider
css_changes = """
        .radio-glider {
            position: absolute;
            top: 6px;
            bottom: 6px;
            left: 6px;
            background: #ffffff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: -1;
            /* Default width if JS hasn't run yet */
            width: 100px; 
        }
        
        .radio-label:has(input[type="radio"]:checked) {
            color: var(--text-main);
            background: transparent;
            box-shadow: none;
        }
"""

if '.radio-glider {' not in html:
    html = html.replace('</style>', css_changes + '\n    </style>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
    
print("HTML updated for radio slider")
