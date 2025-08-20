// src/ui/userInput.ts

// 获取 HTML 元素
const chatInput = document.getElementById('chat-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const bitsButton = document.getElementById('sc-bits-button') as HTMLButtonElement;
const pointsButton = document.getElementById('sc-points-button') as HTMLButtonElement;

// 定义消息类型
export type MessagePayload = {
    type: 'user_message' | 'superchat';
    text: string;
    sc_type?: 'bits' | 'points';
};

// 定义一个回调类型，用于当用户输入被触发时通知外部
type OnSendMessageCallback = (payload: MessagePayload) => void;

export class UserInput {
    private onSendMessageCallback: OnSendMessageCallback | null = null;

    constructor() {
        if (!chatInput || !sendButton || !bitsButton || !pointsButton) {
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
        sendButton.addEventListener('click', () => this.handleSendMessage());
        chatInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                this.handleSendMessage();
            }
        });

        bitsButton.addEventListener('click', () => this.toggleSuperchatButton(bitsButton));
        pointsButton.addEventListener('click', () => this.toggleSuperchatButton(pointsButton));
    }

    /**
     * 处理 Superchat 按钮的互斥选择逻辑。
     * @param button Toggled button.
     */
    private toggleSuperchatButton(button: HTMLButtonElement): void {
        const otherButton = button === bitsButton ? pointsButton : bitsButton;
        if (button.classList.contains('selected')) {
            button.classList.remove('selected');
        } else {
            button.classList.add('selected');
            otherButton.classList.remove('selected');
        }
    }

    /**
     * 处理发送消息的逻辑。
     */
    private handleSendMessage(): void {
        const message = chatInput.value.trim();
        if (!message) {
            console.warn("Attempted to send empty message.");
            return;
        }

        let payload: MessagePayload;
        const bitsSelected = bitsButton.classList.contains('selected');
        const pointsSelected = pointsButton.classList.contains('selected');

        if (bitsSelected || pointsSelected) {
            payload = {
                type: 'superchat',
                text: message,
                sc_type: bitsSelected ? 'bits' : 'points',
            };
        } else {
            payload = {
                type: 'user_message',
                text: message,
            };
        }

        if (this.onSendMessageCallback) {
            this.onSendMessageCallback(payload);
        } else {
            console.warn("No callback registered for sending message.");
        }
        
        chatInput.value = ''; // 清空输入框
        this.clearSuperchatSelection();
    }

    /**
     * 清除 Superchat 按钮的选中状态。
     */
    private clearSuperchatSelection(): void {
        bitsButton.classList.remove('selected');
        pointsButton.classList.remove('selected');
    }

    /**
     * 设置输入框和发送按钮的禁用状态。
     * @param disabled 是否禁用。
     */
    public setInputDisabled(disabled: boolean): void {
        chatInput.disabled = disabled;
        sendButton.disabled = disabled;
        console.log(`User input elements disabled: ${disabled}`);
    }
}
