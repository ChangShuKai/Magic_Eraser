with open('public/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = "step3.style.display = 'none';"
ad_refresh = """
    // --- 廣告與流量統計重新整理 (SPA 換頁) ---
    // 1. 觸發 Google Analytics 換頁 (如果有安裝 GA4)
    if (typeof gtag === 'function') {
        gtag('event', 'page_view', {
            page_title: document.title,
            page_location: window.location.href,
            page_path: path
        });
    }
    
    // 2. 觸發 Google AdSense 廣告重新載入
    setTimeout(() => {
        try {
            const adElements = document.querySelectorAll('.adsbygoogle');
            if (adElements.length > 0 && typeof adsbygoogle !== 'undefined') {
                // 清空已載入的廣告標記，強制 AdSense 重新抓取
                adElements.forEach(el => {
                    el.removeAttribute('data-adsbygoogle-status');
                    el.innerHTML = '';
                });
                // 重新為每一個版位推送廣告
                for (let i = 0; i < adElements.length; i++) {
                    (adsbygoogle = window.adsbygoogle || []).push({});
                }
            }
        } catch (e) {
            console.error('AdSense refresh error:', e);
        }
    }, 100);
"""

if "gtag('event', 'page_view'" not in content:
    content = content.replace(target, target + "\n" + ad_refresh)
    with open('public/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added ad refresh logic")
