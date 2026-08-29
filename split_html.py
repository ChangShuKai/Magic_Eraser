import os
import re

base_dir = r"d:\書愷\硬碟暫放\Python\去手寫\public"
index_path = os.path.join(base_dir, "index.html")

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add localforage script to the end of the body
localforage_tag = '<script src="https://cdnjs.cloudflare.com/ajax/libs/localforage/1.10.0/localforage.min.js"></script>\n    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>'
content = content.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>', localforage_tag)

def extract_div(html, div_id):
    start_tag = f'<div id="{div_id}"'
    start_idx = html.find(start_tag)
    if start_idx == -1: return "", html
    
    open_divs = 0
    i = start_idx
    while i < len(html):
        if html.startswith('<div', i):
            open_divs += 1
            i += 4
        elif html.startswith('</div', i):
            open_divs -= 1
            if open_divs == 0:
                end_idx = i + 6
                return html[start_idx:end_idx], html[:start_idx] + html[end_idx:]
            i += 5
        else:
            i += 1
    return "", html

step1_html, content_no_1 = extract_div(content, "step1")
step2_html, content_no_1_2 = extract_div(content_no_1, "step2")
step3_html, content_no_1_2_3 = extract_div(content_no_1_2, "step3")

# index.html
new_index = content_no_1_2_3.replace('<!-- 預覽畫廊 (動態生成) -->', step1_html + '\n\n        <!-- 預覽畫廊 (動態生成) -->')

# process.html
step2_visible = step2_html.replace('style="display: none;"', 'style="display: block;"')
new_process = content_no_1_2_3.replace('<!-- 預覽畫廊 (動態生成) -->', step2_visible + '\n\n        <!-- 預覽畫廊 (動態生成) -->')
new_process = new_process.replace('<title>Magic Eraser 考卷手寫去除</title>', '<title>Magic Eraser - 處理設定</title>')

# download.html
step3_visible = step3_html.replace('style="display: none;"', 'style="display: block;"')
new_download = content_no_1_2_3.replace('<!-- 預覽畫廊 (動態生成) -->', step3_visible + '\n\n        <!-- 預覽畫廊 (動態生成) -->')
new_download = new_download.replace('<title>Magic Eraser 考卷手寫去除</title>', '<title>Magic Eraser - 下載結果</title>')

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(new_index)

with open(os.path.join(base_dir, "process.html"), 'w', encoding='utf-8') as f:
    f.write(new_process)

with open(os.path.join(base_dir, "download.html"), 'w', encoding='utf-8') as f:
    f.write(new_download)

print("HTML files split successfully.")
