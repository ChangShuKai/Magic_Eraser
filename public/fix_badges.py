import re

with open('d:/書愷/硬碟暫放/Python/去手寫/public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

if '.badge {' not in content:
    badge_css = """
        .badge {
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 12px;
            background: #f3f4f6;
            color: #4b5563;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .badge-output {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }
    </style>"""
    content = content.replace('</style>', badge_css)

    with open('d:/書愷/硬碟暫放/Python/去手寫/public/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Badges CSS added.")
else:
    print("Badges CSS already exists.")
