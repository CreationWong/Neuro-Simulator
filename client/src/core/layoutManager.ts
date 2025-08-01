// src/core/layoutManager.ts

export class LayoutManager {
    private viewportElement: HTMLDivElement;
    private areaElement: HTMLDivElement;
    private resizeObserver: ResizeObserver;

    constructor() {
        this.viewportElement = document.getElementById('stream-display-viewport') as HTMLDivElement;
        this.areaElement = document.getElementById('stream-display-area') as HTMLDivElement;

        if (!this.viewportElement || !this.areaElement) {
            throw new Error("LayoutManager: Required viewport or area element not found in DOM!");
        }
        
        // 使用 .bind(this) 确保 handleResize 中的 this 指向 LayoutManager 实例
        this.resizeObserver = new ResizeObserver(this.handleResize.bind(this));
    }

    /**
     * 当 viewport 尺寸变化时由 ResizeObserver 调用
     * @param entries 尺寸变化的元素条目
     */
    private handleResize(entries: ResizeObserverEntry[]): void {
        for (const entry of entries) {
            // 使用 contentRect 获取元素的内部尺寸，不包括 padding 和 border
            const { width, height } = entry.contentRect;
            this.updateLayout(width, height);
        }
    }

    /**
     * 根据视口尺寸，计算并应用 16:9 内容区的尺寸
     * @param viewportWidth 视口宽度
     * @param viewportHeight 视口高度
     */
    private updateLayout(viewportWidth: number, viewportHeight: number): void {
        if (viewportWidth === 0 || viewportHeight === 0) return;

        const viewportRatio = viewportWidth / viewportHeight;
        const targetRatio = 16 / 9;
        
        let newWidth: number;
        let newHeight: number;

        if (viewportRatio > targetRatio) {
            // 视口比 16:9 更宽 => 高度占满，宽度按比例缩放 (左右黑边)
            newHeight = viewportHeight;
            newWidth = newHeight * targetRatio;
        } else {
            // 视口比 16:9 更高或相等 => 宽度占满，高度按比例缩放 (上下黑边)
            newWidth = viewportWidth;
            newHeight = newWidth / targetRatio;
        }

        this.areaElement.style.width = `${newWidth}px`;
        this.areaElement.style.height = `${newHeight}px`;
    }

    /**
     * 启动布局管理器，开始监听尺寸变化
     */
    public start(): void {
        this.resizeObserver.observe(this.viewportElement);
        // 立即执行一次布局计算，以设置初始状态
        this.updateLayout(this.viewportElement.clientWidth, this.viewportElement.clientHeight);
        console.log("LayoutManager started and observing.");
    }

    /**
     * 停止监听
     */
    public stop(): void {
        this.resizeObserver.disconnect();
        console.log("LayoutManager stopped.");
    }
}