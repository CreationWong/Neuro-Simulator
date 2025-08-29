// src/stream/neuroAvatar.ts
import { NeuroAvatarStage } from '../types/common';

const neuroStaticAvatarContainer = document.getElementById('neuro-static-avatar-container') as HTMLDivElement;

export class NeuroAvatar {
    constructor() {
        if (!neuroStaticAvatarContainer) {
            console.error("NeuroAvatar: Required avatar container element not found in DOM!");
        } else {
            console.log("NeuroAvatar initialized.");
            this.setStage(NeuroAvatarStage.HIDDEN, true);
        }
    }

    /**
     * 开始立绘的完整入场动画序列。
     * @param onComplete 可选的回调函数，在动画序列完成后调用。
     */
    public startIntroAnimation(onComplete?: () => void): void {
        console.log("Starting Neuro intro animation sequence...");
        
        // 1. 立即显示在 Step 1 的位置 (露出头顶)
        this.setStage(NeuroAvatarStage.STEP1);
        
        // 2. 等待 2 秒
        setTimeout(() => {
            console.log("Animating to Step 2...");
            // 3. 触发到 Step 2 的动画
            this.setStage(NeuroAvatarStage.STEP2);

            // 4. 等待 1 秒 (动画时长)
            setTimeout(() => {
                console.log("Neuro intro animation sequence finished.");
                // 动画完成后，调用回调
                if (onComplete) {
                    onComplete();
                }
            }, 1000); // Step 2 动画时长

        }, 2000); // Step 1 停留时长
    }

    /**
     * 根据指定的阶段立即设置 Neuro 立绘的显示和位置。
     * @param stage 要设置的阶段 ("hidden", "step1", "step2")。
     * @param initialSetup 如果为 true，则立即设置样式，不进行过渡动画。
     */
    public setStage(stage: string, initialSetup: boolean = false): void {
        if (!neuroStaticAvatarContainer) return;

        const baseTransition = 'transform 0.5s ease-in-out';

        if (initialSetup) {
            neuroStaticAvatarContainer.style.transition = 'none';
            neuroStaticAvatarContainer.offsetHeight; 
        } else {
            // 为 stage2 动画设置特定的过渡
            if (stage === NeuroAvatarStage.STEP2) {
                neuroStaticAvatarContainer.style.transition = `bottom 1s cubic-bezier(0.4, 0.0, 1, 1), ${baseTransition}`;
            } else {
                // 其他阶段只保留 transform 的过渡
                neuroStaticAvatarContainer.style.transition = baseTransition;
            }
        }
        
        switch (stage) {
            case NeuroAvatarStage.HIDDEN:
                neuroStaticAvatarContainer.style.visibility = 'hidden';
                neuroStaticAvatarContainer.style.bottom = '-207%';
                neuroStaticAvatarContainer.style.left = '70%';
                neuroStaticAvatarContainer.style.zIndex = '10'; 
                break;
            case NeuroAvatarStage.STEP1:
                neuroStaticAvatarContainer.style.visibility = 'visible';
                neuroStaticAvatarContainer.style.bottom = '-207%'; // Step1 的 y 轴位置
                neuroStaticAvatarContainer.style.left = '70%';
                // Z-index 调高，确保它在视频之上
                neuroStaticAvatarContainer.style.zIndex = '15';
                break;
            case NeuroAvatarStage.STEP2:
                neuroStaticAvatarContainer.style.visibility = 'visible';
                neuroStaticAvatarContainer.style.bottom = '-125%'; // Step2 的 y 轴位置，触发 CSS transition
                neuroStaticAvatarContainer.style.left = '70%';
                neuroStaticAvatarContainer.style.zIndex = '15';
                break;
        }
    }

    public triggerSpin(): void {
        if (!neuroStaticAvatarContainer) return;

        console.log("Triggering avatar spin animation.");

        // Add the animation class
        neuroStaticAvatarContainer.classList.add('spin-animation');

        // Remove the class after the animation completes (1 second)
        setTimeout(() => {
            neuroStaticAvatarContainer.classList.remove('spin-animation');
            console.log("Avatar spin animation finished.");
        }, 1000);
    }

    public triggerZoom(): void {
        if (!neuroStaticAvatarContainer) return;
        console.log("Triggering avatar zoom-in animation.");
        neuroStaticAvatarContainer.classList.add('zoom-in');
    }

    public resetZoom(): void {
        if (!neuroStaticAvatarContainer) return;
        if (neuroStaticAvatarContainer.classList.contains('zoom-in')) {
            console.log("Resetting avatar zoom.");
            neuroStaticAvatarContainer.classList.remove('zoom-in');
        }
    }
}