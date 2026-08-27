import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_tag = '<div class="upload-area" id="dropZone"'
end_tag = '<!-- 預覽畫廊 (動態生成) -->'

start_idx = content.find(start_tag)
end_idx = content.find(end_tag)

if start_idx != -1 and end_idx != -1:
    new_block = '''
        <!-- STEP 1: Upload -->
        <div id="step1" class="step-container">
            <div class="upload-area" id="dropZone" onclick="document.getElementById('fileInput').click()">
                <svg class="upload-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z" />
                </svg>
                <h3>點擊或拖曳考卷圖片至此</h3>
                <p>支援 JPG, PNG 高畫質處理</p>
                <span class="limit-text" id="limitText">一次最多支援上傳 3 張圖片</span>
                <input type="file" id="fileInput" accept="image/png, image/jpeg, image/jpg" multiple style="display: none;">
            </div>
            <div class="action-area" id="step1Actions" style="display: none; margin-top: 20px;">
                <button id="goToStep2Btn" class="btn" style="background: var(--accent); color: white;">下一步：設定與去除</button>
            </div>
        </div>

        <!-- STEP 2: Settings & Process -->
        <div id="step2" class="step-container" style="display: none;">
            <div class="settings-card">
                <div class="settings-title">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--primary);">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                    處理參數設定
                </div>
                <div class="settings-group">
                    <div class="setting-section">
                        <span class="setting-label">要去除的顏色目標</span>
                        <div class="radio-group" style="position: relative; z-index: 1;">
                            <div class="radio-glider"></div>
                            <label class="radio-label">
                                <input type="radio" name="color_type" value="red">
                                <span>🔴 紅色筆跡</span>
                            </label>
                            <label class="radio-label">
                                <input type="radio" name="color_type" value="blue">
                                <span>🔵 藍色筆跡</span>
                            </label>
                            <label class="radio-label">
                                <input type="radio" name="color_type" value="both" checked>
                                <span>🌈 所有彩色</span>
                            </label>
                        </div>
                    </div>
                    <div class="setting-section">
                        <span class="setting-label">進階畫質增強</span>
                        <div class="toggle-group">
                            <div style="display: flex; flex-direction: column; gap: 12px;">
                                <label class="toggle-label" id="label_inpaint">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span class="toggle-text">✨ 使用 AI 智慧修補 (Inpaint)</span>
                                        <span class="vip-badge">SVIP專屬</span>
                                        <span class="beta-badge">BETA</span>
                                    </div>
                                    <input type="checkbox" id="cb_inpaint">
                                    <div class="toggle-switch"></div>
                                </label>
                                <div style="display: flex; align-items: center; gap: 8px; padding: 0 4px;">
                                    <span style="font-size: 0.85rem; color: #6b7280; font-weight: 600;">選擇模型：</span>
                                    <select id="inpaint_model" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db; font-size: 0.85rem; outline: none; background: #fff; cursor: pointer; flex: 1;">
                                        <option value="klareo-1-flash">Klareo-1 flash</option>
                                    </select>
                                </div>
                            </div>
                            <label class="toggle-label" id="label_enhance">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span class="toggle-text">🌓 增強黑白對比度</span>
                                    <span class="vip-badge">SVIP專屬</span>
                                </div>
                                <input type="checkbox" id="cb_enhance">
                                <div class="toggle-switch"></div>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <div class="action-area">
                <button id="backToStep1Btn" class="btn" style="background: #94a3b8; color: white;">上一步</button>
                <button id="processBtn" class="btn" disabled>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
                    開始智能去除 (<span id="fileCount">0</span>)
                </button>
            </div>
            
            <div id="status">等待上傳圖片...</div>
            <div class="progress-bar" id="progressBarContainer">
                <div class="progress-fill" id="progressBar"></div>
            </div>
        </div>

        <!-- STEP 3: Download -->
        <div id="step3" class="step-container" style="display: none;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: var(--success); margin-bottom: 10px;">🎉 處理完成！</h2>
                <p style="color: var(--text-muted);">您的圖片已成功去除手寫筆跡</p>
            </div>
            <div class="action-area">
                <button id="restartBtn" class="btn" style="background: #94a3b8; color: white;" onclick="location.reload()">處理其他圖片</button>
                <button id="downloadAllBtn" class="btn btn-success" style="display: inline-flex;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    下載全部結果
                </button>
            </div>
        </div>

'''
    content = content[:start_idx] + new_block + content[end_idx:]
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated index.html")
else:
    print("Not found")
