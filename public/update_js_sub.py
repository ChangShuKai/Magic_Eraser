import re

js_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/app.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

js = js.replace("subBtn.style.display = isUserVIP ? 'none' : 'inline-flex';", "subBtn.style.display = 'inline-flex';")
js = js.replace("if (subBtn) subBtn.style.display = 'inline-block';", "if (subBtn) subBtn.style.display = 'inline-flex';")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js)
    
print("JS updated for always showing subscribe pill")
