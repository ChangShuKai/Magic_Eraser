import re

# Update HTML
html_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Make sure button has id "payBtn"
old_btn = r'<button type="button" class="btn vip-btn" style="width: 100%;" onclick="alert\(\'尚未串接金流\'\)">前往付款</button>'
new_btn = """<button type="button" id="payBtn" class="btn vip-btn" style="width: 100%;" onclick="alert('尚未串接金流')">前往付款</button>
            <div id="currentPlanIndicator" style="display: none; padding: 14px 24px; width: 100%; background: #f3f4f6; color: #4b5563; border-radius: 12px; font-weight: bold; margin-top: 10px;">目前已是 SVIP 方案</div>"""

if 'id="payBtn"' not in html:
    html = re.sub(old_btn, new_btn, html)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)


# Update JS
js_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/app.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

# Add logic for payBtn and currentPlanIndicator
js_update_vip = """
                if (limitText) {
                    limitText.innerText = isUserVIP ? "SVIP 無限制上傳張數" : "一次最多支援上傳 3 張圖片";
                }
                const payBtn = document.getElementById('payBtn');
                const planIndicator = document.getElementById('currentPlanIndicator');
                if (payBtn && planIndicator) {
                    payBtn.style.display = isUserVIP ? 'none' : 'inline-block';
                    planIndicator.style.display = isUserVIP ? 'block' : 'none';
                }
"""

js_update_error = """
                if (limitText) limitText.innerText = "一次最多支援上傳 3 張圖片";
                const payBtn = document.getElementById('payBtn');
                const planIndicator = document.getElementById('currentPlanIndicator');
                if (payBtn && planIndicator) {
                    payBtn.style.display = 'inline-block';
                    planIndicator.style.display = 'none';
                }
"""

js_update_logout = """
        const limitText = document.getElementById('limitText');
        if (limitText) limitText.innerText = "一次最多支援上傳 3 張圖片";
        const payBtn = document.getElementById('payBtn');
        const planIndicator = document.getElementById('currentPlanIndicator');
        if (payBtn && planIndicator) {
            payBtn.style.display = 'inline-block';
            planIndicator.style.display = 'none';
        }
"""

if "const payBtn = document.getElementById('payBtn');" not in js:
    js = js.replace('if (limitText) {\n                    limitText.innerText = isUserVIP ? "SVIP 無限制上傳張數" : "一次最多支援上傳 3 張圖片";\n                }', js_update_vip.strip())
    js = js.replace('if (limitText) limitText.innerText = "一次最多支援上傳 3 張圖片";\n            }\n        } catch (err) {', js_update_error.strip() + '\n            }\n        } catch (err) {')
    # wait, the error handler actually has:
    js = js.replace('if (limitText) limitText.innerText = "一次最多支援上傳 3 張圖片";\n            }\n        }\n    } else {', js_update_error.strip() + '\n            }\n        }\n    } else {')
    js = js.replace("if (limitText) limitText.innerText = \"一次最多支援上傳 3 張圖片\";\n    }\n}", js_update_logout.strip() + "\n    }\n}")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js)

print("Updated HTML and JS")
