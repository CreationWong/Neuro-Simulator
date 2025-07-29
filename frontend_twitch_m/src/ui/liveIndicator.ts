// src/ui/liveIndicator.ts

export class LiveIndicator {
    private indicatorElement: HTMLDivElement;

    constructor() {
        this.indicatorElement = document.querySelector('.live-indicator-rect') as HTMLDivElement;
        if (!this.indicatorElement) {
            throw new Error("LiveIndicator: Required .live-indicator-rect element not found in DOM!");
        }
        // 应用启动时，默认是未连接状态，所以先隐藏指示器
        this.hide();
    }

    /**
     * 显示 "LIVE" 指示器。
     */
    public show(): void {
        this.indicatorElement.classList.remove('hidden');
    }

    /**
     * 隐藏 "LIVE" 指示器。
     */
    public hide(): void {
        this.indicatorElement.classList.add('hidden');
    }
}