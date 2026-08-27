with open('public/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = "window.addEventListener('popstate', handleRoute);"
if target in content:
    content = content.replace(target, "handleRoute();\n" + target)

with open('public/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed init')
