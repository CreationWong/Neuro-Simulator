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

        const seekAfterPlay = () => {
            if (isFinite(startupVideo.duration) && initialProgress > 0.1 && initialProgress < startupVideo.duration) {
                startupVideo.currentTime = initialProgress;
                console.log(`Seeked to: ${initialProgress.toFixed(2)}s.`);
            }
        };

        // 1. 总是先尝试有声播放
        startupVideo.muted = false;
        const playPromise = startupVideo.play();

        if (playPromise !== undefined) {
            playPromise.then(() => {
                // 有声播放成功！
                console.log("Unmuted autoplay successful.");
                seekAfterPlay();
            }).catch(error => {
                // 有声播放失败，被浏览器阻止
                console.warn("Unmuted autoplay failed. Showing unmute prompt and falling back to muted playback.", error);
                
                // 2. 显示交互提示按钮
                muteButton.show();

                // 3. 回退到静音播放
                startupVideo.muted = true;
                const mutedPlayPromise = startupVideo.play();
                mutedPlayPromise.then(() => {
                    console.log("Muted fallback playback started.");
                    seekAfterPlay();
                }).catch(mutedError => {
                    console.error("Muted fallback playback also failed. This is unexpected.", mutedError);
                });
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