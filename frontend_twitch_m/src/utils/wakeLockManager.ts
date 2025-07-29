// src/utils/wakeLockManager.ts

export class WakeLockManager {
    private wakeLockSentinel: WakeLockSentinel | null = null;
    private isSupported: boolean;

    constructor() {
        this.isSupported = 'wakeLock' in navigator;
        if (!this.isSupported) {
            console.warn("Wake Lock API is not supported in this browser. The device may go to sleep during playback.");
        } else {
            console.log("WakeLockManager initialized. API is supported.");
        }
    }

    /**
     * 请求并激活屏幕唤醒锁。
     */
    public async requestWakeLock(): Promise<void> {
        if (!this.isSupported || this.wakeLockSentinel) {
            return;
        }

        try {
            this.wakeLockSentinel = await navigator.wakeLock.request('screen');
            this.wakeLockSentinel.addEventListener('release', () => {
                console.log('Wake Lock was released by the browser.');
                this.wakeLockSentinel = null;
            });
            console.log('Wake Lock is active.');

            // 当页面从隐藏状态恢复时，重新请求锁
            document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));

        } catch (err: any) {
            console.error(`Failed to acquire Wake Lock: ${err.name}, ${err.message}`);
            this.wakeLockSentinel = null;
        }
    }

    /**
     * 释放屏幕唤醒锁。
     */
    public async releaseWakeLock(): Promise<void> {
        if (this.wakeLockSentinel) {
            await this.wakeLockSentinel.release();
            this.wakeLockSentinel = null;
            console.log('Wake Lock has been released.');
        }
        // 移除事件监听器，避免不必要的检查
        document.removeEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    }

    /**
     * 处理页面可见性变化的事件。
     */
    private async handleVisibilityChange(): Promise<void> {
        if (this.wakeLockSentinel === null && document.visibilityState === 'visible') {
            console.log("Page is visible again, re-acquiring Wake Lock...");
            await this.requestWakeLock();
        }
    }
}