// src/stream/videoPlayer.ts

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
     * 显示欢迎视频叠加层并确保其播放。
     * @param initialProgress 可选，视频的初始播放进度（秒）。
     */
    public showAndPlayVideo(initialProgress: number = 0): void {
        if (!startupVideoOverlay || !startupVideo) {
            console.error("VideoPlayer: Cannot show and play video, elements are missing.");
            return;
        }

        startupVideoOverlay.classList.remove('hidden'); 
        
        // --- *** 修改点在这里 *** ---
        // 将视频的 z-index 设置为 10，低于立绘的 z-index (15)
        startupVideoOverlay.style.zIndex = '10'; 
        
        startupVideo.currentTime = initialProgress; 
        
        startupVideo.play().then(() => {
            console.log(`Startup video started from ${initialProgress.toFixed(2)}s.`);
        }).catch(e => {
            console.warn("Startup video autoplay prevented or failed:", e);
        });
    }

    /**
     * 暂停视频播放。
     */
    public pauseVideo(): void {
        if (startupVideo) {
            startupVideo.pause();
            console.log("Startup video paused.");
        }
    }

    /**
     * 隐藏欢迎视频叠加层。
     */
    public hideVideo(): void {
        if (startupVideoOverlay) {
            startupVideoOverlay.classList.add('hidden');
            // 可以选择性地将 z-index 恢复到更低的值
            // startupVideoOverlay.style.zIndex = '5';
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