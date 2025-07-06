// src/ui/neuroCaption.ts

const neuroCaptionElement = document.getElementById('neuro-caption') as HTMLDivElement;
let currentTimeout: ReturnType<typeof setTimeout> | null = null; // 用于清除之前的逐词显示计时器

/**
 * 显示 Neuro 的实时字幕，并支持逐词显示。
 * @param text 要显示的字幕文本。
 * @param duration 可选，该段文本对应的音频时长（秒）。如果提供，将尝试逐词显示。
 */
export function showNeuroCaption(text: string, duration?: number): void {
    if (!neuroCaptionElement) {
        console.error("NeuroCaption: Caption element not found in DOM!");
        return;
    }

    // 清除任何之前的逐词显示计时器
    if (currentTimeout) {
        clearTimeout(currentTimeout);
        currentTimeout = null;
    }

    neuroCaptionElement.textContent = ''; // 先清空内容
    neuroCaptionElement.classList.add('show'); // 确保字幕显示

    if (duration && text.trim().length > 0) {
        const words = text.split(/\s+/).filter(word => word.length > 0); // 拆分单词，处理多空格
        if (words.length === 0) { // 如果没有有效单词，直接显示整句
            neuroCaptionElement.textContent = text;
            return;
        }

        const totalChars = text.length;
        let displayedText = '';
        let currentTime = 0;

        const displayWord = (index: number) => {
            if (index < words.length) {
                const word = words[index];
                // 简单的估算：每个单词的显示时间与该单词包含的字符数成正比
                // 这里的 1.2 是一个调整系数，可以根据实际效果调整
                const wordDuration = (word.length / totalChars) * duration! * 1.05; 
                
                // 确保至少有一个最小延迟，避免过快显示
                const actualDelay = Math.max(50, wordDuration * 1000); 

                displayedText += (index > 0 ? ' ' : '') + word;
                neuroCaptionElement.textContent = displayedText;

                // 调度下一个词的显示
                currentTimeout = setTimeout(() => displayWord(index + 1), actualDelay);
            } else {
                // 所有词都显示完毕，保持显示状态直到音频结束或被隐藏
                currentTimeout = null;
            }
        };
        
        displayWord(0); // 开始显示第一个词
        console.log(`Starting word-by-word caption for: "${text.substring(0, 30)}..." (duration: ${duration}s)`);
    } else {
        // 没有提供时长或文本为空，直接显示完整文本
        neuroCaptionElement.textContent = text;
        console.log(`Displaying full caption: "${text.substring(0, 30)}..."`);
    }
}

/**
 * 隐藏 Neuro 的实时字幕并清空内容。
 */
export function hideNeuroCaption(): void {
    if (!neuroCaptionElement) {
        console.error("NeuroCaption: Caption element not found in DOM!");
        return;
    }
    // 清除任何正在进行的逐词显示计时器
    if (currentTimeout) {
        clearTimeout(currentTimeout);
        currentTimeout = null;
    }
    neuroCaptionElement.classList.remove('show'); // 移除 CSS 类来隐藏字幕
    neuroCaptionElement.textContent = ''; // 清空字幕内容
    console.log("NeuroCaption hidden and cleared.");
}

// 在模块加载时进行初始化检查
(() => {
    if (!neuroCaptionElement) {
        console.error("neuroCaption.ts: Could not find #neuro-caption element.");
    } else {
        console.log("NeuroCaption module initialized.");
    }
})();
