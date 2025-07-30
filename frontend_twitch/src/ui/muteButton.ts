import { MuteButtonElement } from "../types/common";

export class MuteButton {
    private button: MuteButtonElement | null = null;

    public create(): MuteButtonElement {
        // 创建静音按钮元素
        this.button = document.createElement('button');
        this.button.id = 'mute-button';
        this.button.className = 'mute-button';
        this.button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4.75H8a2 2 0 0 0-2 2v10.5a2 2 0 0 0 2 2h3"></path>
                <path d="M14 18.5V6.5l4 4v4l-4 4z"></path>
                <line x1="2" y1="2" x2="22" y2="22" stroke="currentColor" stroke-width="2"></line>
            </svg>
        `;
        
        // 添加点击事件监听器
        this.button.addEventListener('click', () => {
            // 点击按钮后隐藏它
            this.hide();
        });
        
        return this.button;
    }

    public show(): void {
        if (this.button) {
            this.button.style.display = 'flex';
        }
    }

    public hide(): void {
        if (this.button) {
            this.button.style.display = 'none';
        }
    }

    public getElement(): MuteButtonElement | null {
        return this.button;
    }
}