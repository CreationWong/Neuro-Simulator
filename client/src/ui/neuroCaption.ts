// src/ui/neuroCaption.ts

const neuroCaptionElement = document.getElementById('neuro-caption') as HTMLDivElement;
const streamDisplayArea = document.getElementById('stream-display-area');

const MIN_FONT_SIZE_PX = 16;
const FONT_ADJUSTMENT_STEP_PX = 2; // 步进调整为 2
const HEIGHT_THRESHOLD_PERCENT = 0.4; // 高度门槛调整为 40%

/**
 * Adjusts the font size of the caption based on its height relative to the container.
 */
function adjustFontSize(): void {
    if (!neuroCaptionElement || !streamDisplayArea) return;

    // Reset to CSS-defined font-size to get the "natural" height at max size
    neuroCaptionElement.style.fontSize = '';

    const containerHeight = streamDisplayArea.offsetHeight;
    // Must have content to measure, otherwise height is 0
    if (neuroCaptionElement.textContent === '' || containerHeight === 0) return;
    
    const captionHeight = neuroCaptionElement.offsetHeight;

    if (captionHeight > containerHeight * HEIGHT_THRESHOLD_PERCENT) {
        // Get the computed font size in pixels to start shrinking from
        const computedStyle = window.getComputedStyle(neuroCaptionElement);
        let currentFontSize = parseFloat(computedStyle.fontSize);

        // Shrink font size until it fits or hits the minimum size
        while (neuroCaptionElement.offsetHeight > containerHeight * HEIGHT_THRESHOLD_PERCENT && currentFontSize > MIN_FONT_SIZE_PX) {
            currentFontSize -= FONT_ADJUSTMENT_STEP_PX;
            neuroCaptionElement.style.fontSize = `${currentFontSize}px`;
        }
        
        // If it's still too tall, it must have hit the minimum size.
        // In this case, we cap it at the minimum size and let it overflow.
        if (neuroCaptionElement.offsetHeight > containerHeight * HEIGHT_THRESHOLD_PERCENT) {
             neuroCaptionElement.style.fontSize = `${MIN_FONT_SIZE_PX}px`;
        }
    }
}


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
            neuroCaptionElement.textContent += (neuroCaptionElement.textContent ? ' ' : '') + text;
            adjustFontSize();
            return;
        }

        const totalChars = text.length;
        let displayedText = neuroCaptionElement.textContent; // 保留现有文本

        const displayWord = (index: number) => {
            if (index < words.length) {
                const word = words[index];
                const wordDuration = (word.length / totalChars) * duration! * 1.01;
                const actualDelay = Math.max(50, wordDuration * 1000);

                displayedText += (displayedText.length > 0 ? ' ' : '') + word;
                neuroCaptionElement.textContent = displayedText;
                adjustFontSize();

                currentTimeout = setTimeout(() => displayWord(index + 1), actualDelay);
            } else {
                currentTimeout = null;
            }
        };
        
        displayWord(0);
        console.log(`Starting word-by-word caption for: "${text.substring(0, 30)}..." (duration: ${duration}s)`);
    } else {
        neuroCaptionElement.textContent += (neuroCaptionElement.textContent ? ' ' : '') + text; // 追加文本而不是替换
        adjustFontSize();
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
    neuroCaptionElement.style.fontSize = ''; // 重置字体大小，恢复到CSS默认值
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
    if (!neuroCaptionElement || !streamDisplayArea) {
        console.error("neuroCaption.ts: Could not find #neuro-caption or #stream-display-area element.");
    } else {
        console.log("NeuroCaption module initialized.");
    }
})();
