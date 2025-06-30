// src/ui/neuroCaption.ts

// 获取 HTML 元素
const neuroCaptionElement = document.getElementById('neuro-caption') as HTMLDivElement;

/**
 * 显示 Neuro 的实时字幕。
 * @param text 要显示的字幕文本。
 */
export function showNeuroCaption(text: string): void {
    if (!neuroCaptionElement) {
        console.error("NeuroCaption: Caption element not found in DOM!");
        return;
    }
    neuroCaptionElement.textContent = text;
    neuroCaptionElement.classList.add('show'); // 添加 CSS 类来显示字幕 (如果有过渡效果)
}

/**
 * 隐藏 Neuro 的实时字幕并清空内容。
 */
export function hideNeuroCaption(): void {
    if (!neuroCaptionElement) {
        console.error("NeuroCaption: Caption element not found in DOM!");
        return;
    }
    neuroCaptionElement.classList.remove('show'); // 移除 CSS 类来隐藏字幕
    neuroCaptionElement.textContent = ''; // 清空字幕内容
}

// 在模块加载时进行初始化检查
(() => {
    if (!neuroCaptionElement) {
        console.error("neuroCaption.ts: Could not find #neuro-caption element.");
    } else {
        console.log("NeuroCaption module initialized.");
    }
})();