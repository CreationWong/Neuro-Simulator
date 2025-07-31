import { MuteButtonElement } from "../types/common";
import { singletonManager } from "../core/singletonManager";

export class MuteButton {
    private button: MuteButtonElement | null = null;
    private isMuted: boolean = true; // 默认为静音状态

    public create(): MuteButtonElement {
        // 获取HTML中已存在的按钮元素
        this.button = document.getElementById('mute-button') as MuteButtonElement;
        
        if (this.button) {
            // 添加点击事件监听器到按钮本身
            this.button.addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止事件冒泡
                this.unmute(); // 点击按钮时解除静音
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

    public unmute(): void {
        this.isMuted = false;
        this.hide(); // 解除静音后隐藏按钮
        this.updateMediaElements();
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