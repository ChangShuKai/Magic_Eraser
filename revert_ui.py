import re

with open('public/style.css', 'r', encoding='utf-8') as f:
    style_css = f.read()

auth_modal_content_old = """.auth-modal-content {
    max-width: 900px !important;
    padding: 0 !important;
    border-radius: 24px !important;
    overflow: hidden;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    background: transparent !important;
    border: none !important;
    zoom: 0.85;
}"""
style_css = re.sub(r'\.auth-modal-content\s*\{[^}]*\}', auth_modal_content_old, style_css)

auth_layout_old = """.auth-layout {
    display: flex;
    flex-direction: column;
    width: 100%;
    background: #ffffff;
    min-height: 600px;
}"""
style_css = re.sub(r'\.auth-layout\s*\{[^}]*\}', auth_layout_old, style_css)

auth_left_old = """.auth-left {
    flex: 1;
    padding: 3rem 2.5rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}"""
style_css = re.sub(r'\.auth-left\s*\{[^}]*\}', auth_left_old, style_css)

with open('public/style.css', 'w', encoding='utf-8') as f:
    f.write(style_css)

print("Done reverting and adding zoom!")
