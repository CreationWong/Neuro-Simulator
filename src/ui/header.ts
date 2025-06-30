// src/ui/header.ts

// 获取 HTML 元素
const resetButton = document.getElementById('reset-button') as HTMLAnchorElement;

// 定义一个回调类型，用于当重置操作被触发时通知外部
type OnResetCallback = () => void;

export class Header {
    private onResetCallback: OnResetCallback | null = null;

    constructor() {
        if (!resetButton) {
            console.error("Header: Required reset button element not found in DOM!");
        } else {
            this.setupEventListeners();
            console.log("Header initialized.");
        }
    }

    /**
     * 设置重置操作的回调函数。
     * @param callback 当用户点击重置按钮时调用的函数。
     */
    public onReset(callback: OnResetCallback): void {
        this.onResetCallback = callback;
    }

    /**
     * 设置事件监听器。
     */
    private setupEventListeners(): void {
        if (resetButton) {
            resetButton.addEventListener('click', (event) => {
                event.preventDefault(); // 阻止默认的链接行为
                this.handleReset();
            });
        }
    }

    /**
     * 处理重置按钮点击的逻辑。
     */
    private handleReset(): void {
        console.log("Reset button clicked.");
        if (this.onResetCallback) {
            this.onResetCallback(); // 调用外部注册的回调
        } else {
            console.warn("No callback registered for reset action.");
        }
    }
}