import re

js_path = 'd:/書愷/硬碟暫放/Python/去手寫/public/app.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

glider_js = """
// Radio group glider animation
function updateRadioGlider() {
    const checked = document.querySelector('input[name="color_type"]:checked');
    const glider = document.querySelector('.radio-glider');
    if (checked && glider) {
        const label = checked.closest('.radio-label');
        if (label) {
            glider.style.width = `${label.offsetWidth}px`;
            // parent has 6px padding, so offsetLeft is relative to parent. 
            // We just set transform to the left position.
            // Wait, offsetLeft of label inside radio-group includes the padding of radio-group?
            // Actually, offsetLeft is relative to the offsetParent (which is radio-group since it has position: relative).
            // Since glider has left: 6px, and the first label has offsetLeft: 6px, we need to subtract 6px.
            glider.style.transform = `translateX(${label.offsetLeft - 6}px)`;
        }
    }
}
document.querySelectorAll('input[name="color_type"]').forEach(radio => {
    radio.addEventListener('change', updateRadioGlider);
});
window.addEventListener('resize', updateRadioGlider);
// Run once on load
setTimeout(updateRadioGlider, 100);
"""

if 'updateRadioGlider' not in js:
    js += '\n' + glider_js

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js)
    
print("JS updated for radio slider")
