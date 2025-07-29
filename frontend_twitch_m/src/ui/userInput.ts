// src/ui/userInput.ts

// 获取 HTML 元素
const chatInput = document.getElementById('chat-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;

// 定义一个回调类型，用于当用户输入被触发时通知外部
type OnSendMessageCallback = (message: string) => void;

export class UserInput {
    private onSendMessageCallback: OnSendMessageCallback | null = null;

    constructor() {
        if (!chatInput || !sendButton) {
            console.error("UserInput: Required input elements not found in DOM!");
        } else {
            this.setupEventListeners();
            console.log("UserInput initialized.");
        }
    }

    /**
     * 设置发送消息的回调函数。
     * @param callback 当用户点击发送或按回车时调用的函数。
     */
    public onSendMessage(callback: OnSendMessageCallback): void {
        this.onSendMessageCallback = callback;
    }

    /**
     * 设置事件监听器。
     */
    private setupEventListeners(): void {
        if (sendButton) {
            sendButton.addEventListener('click', () => this.handleSendMessage());
        }
        if (chatInput) {
            chatInput.addEventListener('keypress', (event) => {
                if (event.key === 'Enter') {
                    this.handleSendMessage();
                }
            });
        }
    }

    /**
     * 处理发送消息的逻辑。
     */
    private handleSendMessage(): void {
        if (!chatInput) return;

        const message = chatInput.value.trim();
        if (!message) {
            console.warn("Attempted to send empty message.");
            return; // 如果消息为空，则不发送
        }

        if (this.onSendMessageCallback) {
            this.onSendMessageCallback(message); // 调用外部注册的回调
        } else {
            console.warn("No callback registered for sending message.");
        }
        
        chatInput.value = ''; // 清空输入框
    }

    /**
     * 设置输入框和发送按钮的禁用状态。
     * @param disabled 是否禁用。
     */
    public setInputDisabled(disabled: boolean): void {
        if (chatInput) {
            chatInput.disabled = disabled;
        }
        if (sendButton) {
            sendButton.disabled = disabled;
        }
        console.log(`User input elements disabled: ${disabled}`);
    }
}