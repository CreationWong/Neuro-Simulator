// src/ui/streamTimer.ts

export class StreamTimer {
    private timerElement: HTMLSpanElement;
    private intervalId: number | null = null;
    private streamStartTime: number = 0;

    constructor() {
        this.timerElement = document.getElementById('stream-duration-text') as HTMLSpanElement;
        if (!this.timerElement) {
            throw new Error("StreamTimer: Duration element '#stream-duration-text' not found!");
        }
        this.reset();
    }

    // --- MODIFIED ---
    private formatTime(totalSeconds: number): string {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = Math.floor(totalSeconds % 60);

        const pad = (num: number) => String(num).padStart(2, '0');

        if (hours > 0) {
            return `${hours}:${pad(minutes)}:${pad(seconds)}`;
        } else {
            return `${minutes}:${pad(seconds)}`;
        }
    }

    private updateDisplay(): void {
        if (this.streamStartTime > 0) {
            const elapsedMilliseconds = Date.now() - this.streamStartTime;
            const elapsedSeconds = elapsedMilliseconds / 1000;
            // --- MODIFIED ---
            // 初始化时可能显示 0:00 而不是 NaN:NaN
            this.timerElement.textContent = this.formatTime(Math.max(0, elapsedSeconds));
        }
    }

    public start(initialSeconds: number = 0): void {
        this.stop();
        this.streamStartTime = Date.now() - (initialSeconds * 1000);
        this.updateDisplay();
        this.intervalId = window.setInterval(() => this.updateDisplay(), 1000);
        console.log(`Stream timer started with initial ${initialSeconds.toFixed(2)}s.`);
    }

    public stop(): void {
        if (this.intervalId !== null) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log("Stream timer stopped.");
        }
    }

    public reset(): void {
        this.stop();
        this.streamStartTime = 0;
        // --- MODIFIED ---
        this.timerElement.textContent = "0:00"; // 初始显示
        console.log("Stream timer reset.");
    }
}