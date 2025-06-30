// src/ui/streamTimer.ts

export class StreamTimer {
    private timerElement: HTMLSpanElement;
    private intervalId: number | null = null;
    private streamStartTime: number = 0; // Unix timestamp (ms) of stream start

    constructor() {
        this.timerElement = document.getElementById('stream-duration-text') as HTMLSpanElement;
        if (!this.timerElement) {
            throw new Error("StreamTimer: Duration element '#stream-duration-text' not found!");
        }
        this.reset();
    }

    private formatTime(totalSeconds: number): string {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = Math.floor(totalSeconds % 60);

        const pad = (num: number) => String(num).padStart(2, '0');

        return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }

    private updateDisplay(): void {
        if (this.streamStartTime > 0) {
            const elapsedMilliseconds = Date.now() - this.streamStartTime;
            const elapsedSeconds = elapsedMilliseconds / 1000;
            this.timerElement.textContent = this.formatTime(elapsedSeconds);
        }
    }

    public start(initialSeconds: number = 0): void {
        this.stop(); // Ensure no multiple intervals are running
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
        this.timerElement.textContent = "00:00:00";
        console.log("Stream timer reset.");
    }
}