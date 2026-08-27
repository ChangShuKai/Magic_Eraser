import re

# Update HTML
html_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Make sure button has id "payBtn"
old_btn = r'<button type="button" class="btn vip-btn" style="width: 100%;" onclick="alert\(\'尚未串接金流\'\)">前往付款</button>'
new_btn = """<button type="button" id="payBtn" class="btn vip-btn" style="width: 100%;" onclick="alert('尚未串接金流')">前往付款</button>
            <div id="currentPlanIndicator" style="display: none; padding: 14px 24px; width: 100%; background: #f3f4f6; color: #4b5563; border-radius: 12px; font-weight: bold;">目前已是 SVIP 方案</div>"""

if 'id="payBtn"' not in html:
    html = re.sub(old_btn, new_btn, html)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)


# Update JS
js_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/app.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

# I will append a function to app.js that updates the modal state, and call it in onAuthStateChange
if 'function updateSubscriptionModal' not in js:
    js_func = """
function updateSubscriptionModal(isVip) {
    const payBtn = document.getElementById('payBtn');
    const planIndicator = document.getElementById('currentPlanIndicator');
    if (payBtn && planIndicator) {
        payBtn.style.display = isVip ? 'none' : 'inline-block';
        planIndicator.style.display = isVip ? 'block' : 'none';
    }
}
"""
    js += js_func
    
    # Now find where isUserVIP is updated and insert the function call.
    # In try block: isUserVIP = (!error && data) ? !!data.is_vip : false;
    js = re.sub(r'(isUserVIP = .*?;)', r'\1\n                updateSubscriptionModal(isUserVIP);', js)
    
    # There's also `isUserVIP = false;` in catch block and logout block.
    # We will replace all occurrences of `isUserVIP = false;` (except where it's declared `let isUserVIP = false;`)
    js = re.sub(r'(\s+isUserVIP = false;)', r'\1\n        updateSubscriptionModal(false);', js)

    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js)

print("Updated HTML and JS")
