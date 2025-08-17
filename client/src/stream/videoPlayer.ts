// src/stream/videoPlayer.ts

import { singletonManager } from '../core/singletonManager';

const startupVideoOverlay = document.getElementById('startup-video-overlay') as HTMLDivElement;
const startupVideo = document.getElementById('startup-video') as HTMLVideoElement;

export class VideoPlayer {

    constructor() {
        if (!startupVideoOverlay || !startupVideo) {
            console.error("VideoPlayer: Required video elements not found in DOM!");
        } else {
            console.log("VideoPlayer initialized.");
        }
    }

    /**
     * 显示欢迎视频叠加层并从指定进度开始播放。
     * @param initialProgress 视频的初始播放进度（秒）。
     */
    public showAndPlayVideo(initialProgress: number = 0): void {
        if (!startupVideoOverlay || !startupVideo) {
            console.error("VideoPlayer: Cannot show and play video, elements are missing.");
            return;
        }

        startupVideoOverlay.classList.remove('hidden');
        startupVideoOverlay.style.zIndex = '10';

        const app = singletonManager.getAppInitializer();
        const muteButton = app.getMuteButton();
        startupVideo.muted = muteButton.getIsMuted();

        // 直接调用 play()，这是最强的播放指令
        const playPromise = startupVideo.play();

        if (playPromise !== undefined) {
            playPromise.then(() => {
                // 播放成功开始后，再尝试设置时间点
                if (isFinite(startupVideo.duration) && initialProgress > 0.1 && initialProgress < startupVideo.duration) {
                    startupVideo.currentTime = initialProgress;
                    console.log(`Playback started, then seeked to: ${initialProgress.toFixed(2)}s.`);
                }
            }).catch(error => {
                console.warn("Video play failed. This might be due to browser autoplay restrictions.", error);
            });
        }
    }

    /**
     * 暂停并静音视频。
     */
    public pauseAndMute(): void {
        if (startupVideo) {
            startupVideo.pause();
            startupVideo.muted = true;
            console.log("Startup video paused and muted.");
        }
    }

    /**
     * 隐藏欢迎视频叠加层。
     */
    public hide(): void {
        if (startupVideoOverlay) {
            startupVideoOverlay.classList.add('hidden');
            console.log("Startup video overlay hidden.");
        }
    }

    /**
     * 获取视频总时长。
     * @returns 视频时长（秒），如果不可用则返回 0。
     */
    public getVideoDuration(): number {
        if (startupVideo && !isNaN(startupVideo.duration)) {
            return startupVideo.duration;
        }
        return 0;
    }
}