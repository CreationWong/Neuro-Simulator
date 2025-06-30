// src/services/audioPlayer.ts

// import { WebSocketClient } from './websocketClient'; // 不再需要导入 WebSocketClient 来发送 TTS Finished 信号
import { showNeuroCaption, hideNeuroCaption } from '../ui/neuroCaption'; // 导入字幕显示/隐藏函数

// 定义音频片段的接口
interface AudioSegment {
    text: string;           // 对应的字幕文本
    audio: HTMLAudioElement; // 音频元素实例
}

export class AudioPlayer {
    private audioQueue: AudioSegment[] = []; // 存储音频片段的队列
    private isPlayingAudio: boolean = false; // 标记是否有音频正在播放
    private currentPlayingAudio: HTMLAudioElement | null = null; // 当前正在播放的音频实例
    private allSegmentsReceived: boolean = false; // 标记 Neuro 的一次完整响应的所有片段是否已接收

    // 移除对 WebSocket 客户端的依赖，因为不再发送 TTS 完成信号
    // private neuroWsClient: WebSocketClient; 

    constructor(/* neuroWsClient: WebSocketClient */) { // 构造函数不再接受 neuroWsClient 参数
        // this.neuroWsClient = neuroWsClient; 
        console.log("AudioPlayer initialized.");
    }

    /**
     * 添加一个音频片段到播放队列。
     * @param text 音频对应的字幕文本。
     * @param audioBase64 音频的 Base64 编码数据。
     */
    public addAudioSegment(text: string, audioBase64: string): void {
        const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
        this.audioQueue.push({ text, audio });
        console.log(`Audio segment added to queue. Queue size: ${this.audioQueue.length}`);
        // 如果当前没有音频在播放，立即尝试播放
        if (!this.isPlayingAudio) {
            this.playNextAudioSegment();
        }
    }

    /**
     * 标记所有音频片段已从后端接收完毕。
     * 此时，AudioPlayer 仅需确保播放完所有片段，但不再需要通知后端。
     */
    public setAllSegmentsReceived(): void {
        this.allSegmentsReceived = true;
        console.log("All Neuro audio segments marked as received.");
        // 如果队列已空且没有正在播放的音频，现在只隐藏字幕，不再通知后端
        if (this.audioQueue.length === 0 && !this.isPlayingAudio) {
            hideNeuroCaption();
        }
    }

    /**
     * 播放队列中的下一个音频片段。私有方法，由内部调用。
     */
    private playNextAudioSegment(): void {
        if (this.audioQueue.length > 0 && !this.isPlayingAudio) {
            this.isPlayingAudio = true;
            const currentSegment = this.audioQueue.shift()!; // 获取并移除队列头部的片段
            this.currentPlayingAudio = currentSegment.audio;
            
            showNeuroCaption(currentSegment.text); // 显示当前片段的字幕

            this.currentPlayingAudio.play().then(() => {
                // 音频播放成功启动
            }).catch(e => {
                console.error("Error playing audio segment:", e);
                this.isPlayingAudio = false; // 标记为不再播放
                this.currentPlayingAudio = null; // 清除引用
                this.playNextAudioSegment(); // 尝试播放下一个片段
            });

            this.currentPlayingAudio.addEventListener('ended', () => {
                this.isPlayingAudio = false; // 当前片段播放完毕
                this.currentPlayingAudio = null; // 清除引用
                this.playNextAudioSegment(); // 尝试播放队列中的下一个
            }, { once: true }); // 事件监听器只触发一次
        } else if (this.audioQueue.length === 0 && this.allSegmentsReceived) {
            // 如果队列为空且所有片段都已接收，则表示 Neuro 的一次完整响应已完成
            console.log("Neuro's full audio response played and all segments received.");
            hideNeuroCaption(); // 隐藏字幕
        }
    }

    /**
     * 立即停止所有 Neuro TTS 音频播放并清空队列。
     */
    public stopAllAudio(): void {
        if (this.currentPlayingAudio) {
            this.currentPlayingAudio.pause(); // 暂停当前播放的音频
            this.currentPlayingAudio.currentTime = 0; // 重置播放位置
            this.currentPlayingAudio = null;
        }
        this.audioQueue.length = 0; // 清空音频队列
        this.isPlayingAudio = false;
        this.allSegmentsReceived = false;
        hideNeuroCaption(); // 隐藏字幕
        console.log("Neuro audio playback stopped, queue cleared.");
    }
}