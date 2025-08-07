// src/ui/neuroCaption.ts

const neuroCaptionElement = document.getElementById('neuro-caption') as HTMLDivElement;
let currentTimeout: ReturnType<typeof setTimeout> | null = null; // 用于清除之前的逐词显示计时器
let clearTimeoutHandler: ReturnType<typeof setTimeout> | null = null;
const CAPTION_TIMEOUT_MS = 3000; // 3秒

/**
 * 显示 Neuro 的实时字幕，并支持逐词显示。
 * @param text 要显示的字幕文本。
 * @param duration 可选，该段文本对应的音频时长（秒）。如果提供，将尝试逐词显示。
 */
export function showNeuroCaption(text: string, duration?: number): void {
    if (!neuroCaptionElement) return;

    // 不清除之前的字幕内容
    // neuroCaptionElement.textContent = ''; // 先清空内容
    neuroCaptionElement.classList.add('show'); // 确保字幕显示

    if (duration && text.trim().length > 0) {
        const words = text.split(/\s+/).filter(word => word.length > 0);
        if (words.length === 0) {
            neuroCaptionElement.textContent += text; // 追加文本而不是替换
            return;
        }

        const totalChars = text.length;
        let displayedText = neuroCaptionElement.textContent; // 保留现有文本

        const displayWord = (index: number) => {
            if (index < words.length) {
                const word = words[index];
                const wordDuration = (word.length / totalChars) * duration! * 1.01;
                const actualDelay = Math.max(50, wordDuration * 1000);

                displayedText += (index > 0 ? ' ' : '') + word;
                neuroCaptionElement.textContent = displayedText;

                currentTimeout = setTimeout(() => displayWord(index + 1), actualDelay);
            } else {
                currentTimeout = null;
            }
        };
        
        displayWord(0);
        console.log(`Starting word-by-word caption for: "${text.substring(0, 30)}..." (duration: ${duration}s)`);
    } else {
        neuroCaptionElement.textContent += text; // 追加文本而不是替换
        console.log(`Displaying full caption: "${text.substring(0, 30)}..."`);
    }
}

/**
 * 隐藏 Neuro 的实时字幕并清空内容。
 */
export function hideNeuroCaption(): void {
    if (!neuroCaptionElement) return;
    if (currentTimeout) {
        clearTimeout(currentTimeout);
        currentTimeout = null;
    }
    if (clearTimeoutHandler) {
        clearTimeout(clearTimeoutHandler);
        clearTimeoutHandler = null;
    }
    neuroCaptionElement.classList.remove('show'); // 移除 CSS 类来隐藏字幕
    neuroCaptionElement.textContent = ''; // 清空字幕内容
    console.log("NeuroCaption hidden and cleared.");
}

// 新增：由外部调用，最后一句话后才计时
export function startCaptionTimeout() {
    if (clearTimeoutHandler) clearTimeout(clearTimeoutHandler);
    clearTimeoutHandler = setTimeout(() => {
        hideNeuroCaption();
    }, CAPTION_TIMEOUT_MS);
}

// 在模块加载时进行初始化检查
(() => {
    if (!neuroCaptionElement) {
        console.error("neuroCaption.ts: Could not find #neuro-caption element.");
    } else {
        console.log("NeuroCaption module initialized.");
    }
})();
