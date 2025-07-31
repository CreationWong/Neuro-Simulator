import { MuteButtonElement } from "../types/common";
import { singletonManager } from "../core/singletonManager";

export class MuteButton {
    private button: MuteButtonElement | null = null;
    private isMuted: boolean = true; // 默认为静音状态

    public create(): MuteButtonElement {
        // 获取HTML中已存在的按钮元素
        this.button = document.getElementById('mute-button') as MuteButtonElement;
        
        if (this.button) {
            // 添加点击事件监听器
            this.button.addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止事件冒泡
                this.toggleMute();
            });
        } else {
            console.error("Mute button element not found in DOM!");
        }
        
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

    public toggleMute(): void {
        this.isMuted = !this.isMuted;
        this.updateButtonIcon();
        this.updateMediaElements();
    }

    private updateButtonIcon(): void {
        if (this.button) {
            if (this.isMuted) {
                // 静音图标
                this.button.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4.75H8a2 2 0 0 0-2 2v10.5a2 2 0 0 0 2 2h3"></path>
                        <path d="M14 18.5V6.5l4 4v4l-4 4z"></path>
                        <line x1="2" y1="2" x2="22" y2="22" stroke="currentColor" stroke-width="2"></line>
                    </svg>
                `;
            } else {
                // 取消静音图标
                this.button.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 15v4c0 1.1.9 2 2 2h4l5 5v-5h4c1.1 0 2-.9 2-2v-4"></path>
                        <path d="M17 13h-5.3a4.5 4.5 0 0 1-4.5-4.5c0-1.2.5-2.3 1.3-3.1L3 15"></path>
                    </svg>
                `;
            }
        }
    }

    private updateMediaElements(): void {
        // 更新视频元素的静音状态
        const startupVideo = document.getElementById('startup-video') as HTMLVideoElement;
        if (startupVideo) {
            startupVideo.muted = this.isMuted;
        }

        // 更新音频播放器中的音频元素静音状态
        try {
            const app = singletonManager.getAppInitializer();
            const audioPlayer = app.getAudioPlayer();
            audioPlayer.updateMuteState();
        } catch (e) {
            console.warn("Could not update audio player mute state:", e);
        }
    }

    public getElement(): MuteButtonElement | null {
        return this.button;
    }

    public getIsMuted(): boolean {
        return this.isMuted;
    }
}