import re

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
    
    # Precise replacements
    js = js.replace(
        "isUserVIP = (!error && data) ? !!data.is_vip : false;",
        "isUserVIP = (!error && data) ? !!data.is_vip : false;\n                updateSubscriptionModal(isUserVIP);"
    )
    
    js = js.replace(
        "                isUserVIP = false;\n                document.getElementById('vipPill').style.display = 'none';",
        "                isUserVIP = false;\n                updateSubscriptionModal(false);\n                document.getElementById('vipPill').style.display = 'none';"
    )
    
    js = js.replace(
        "        isUserVIP = false;\n        document.getElementById('vipPill').style.display = 'none';",
        "        isUserVIP = false;\n        updateSubscriptionModal(false);\n        document.getElementById('vipPill').style.display = 'none';"
    )

    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js)

print("Updated JS robustly")
