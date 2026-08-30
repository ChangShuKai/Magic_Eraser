import re

# Fix app.js (change 'block' to 'flex' for step1Actions)
with open('public/app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# The original logic had step1Actions.style.display = 'block';
app_js = app_js.replace("step1Actions.style.display = 'block';", "step1Actions.style.display = 'flex';")

with open('public/app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

# Fix style.css for auth modal
with open('public/style.css', 'r', encoding='utf-8') as f:
    style_css = f.read()

# Add max-height and overflow adjustments
# .auth-modal-content
auth_modal_content_new = """.auth-modal-content {
    max-width: 900px !important;
    padding: 0 !important;
    border-radius: 24px !important;
    overflow: hidden;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    background: transparent !important;
    border: none !important;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
}"""
style_css = re.sub(r'\.auth-modal-content\s*\{[^}]*\}', auth_modal_content_new, style_css)

# .auth-layout
auth_layout_new = """.auth-layout {
    display: flex;
    flex-direction: column;
    width: 100%;
    background: #ffffff;
    min-height: 600px;
    height: 100%;
    max-height: 90vh;
}"""
style_css = re.sub(r'\.auth-layout\s*\{[^}]*\}', auth_layout_new, style_css)

# .auth-left
auth_left_new = """.auth-left {
    flex: 1;
    padding: 3rem 2.5rem;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    overflow-y: auto;
}"""
style_css = re.sub(r'\.auth-left\s*\{[^}]*\}', auth_left_new, style_css)

# .auth-right (needs overflow hidden or auto so it doesn't break rounded corners/gradients, 
# but usually it's fine. It's a flex child. Let's make sure it shrinks properly if needed)
# Actually, the right side is just an image/gradient with text.

with open('public/style.css', 'w', encoding='utf-8') as f:
    f.write(style_css)

print("Done fixing UI!")
