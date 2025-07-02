// src/services/audioPlayer.ts

import { showNeuroCaption, hideNeuroCaption } from '../ui/neuroCaption';

interface AudioSegment {
    text: string;
    audio: HTMLAudioElement;
}

export class AudioPlayer {
    private audioQueue: AudioSegment[] = [];
    private isPlayingAudio: boolean = false;
    private currentPlayingAudio: HTMLAudioElement | null = null;
    private allSegmentsReceived: boolean = false;
    private errorSound: HTMLAudioElement; // <-- 新增：专门用于播放错误音效的实例

    constructor() {
        // 在构造函数中初始化错误音效
        this.errorSound = new Audio('/error.mp3'); // 路径指向 public/error.mp3
        console.log("AudioPlayer initialized.");
    }

    /**
     * 新增：播放预置的错误音效。
     */
    public playErrorSound(): void {
        // 在播放错误音效前，确保停止所有正在进行的语音
        this.stopAllAudio(); 

        console.log("Playing dedicated error sound...");
        this.errorSound.play().catch(e => {
            console.error("Error playing dedicated error sound:", e);
        });
    }

    public addAudioSegment(text: string, audioBase64: string): void {
        const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
        this.audioQueue.push({ text, audio });
        console.log(`Audio segment added to queue. Queue size: ${this.audioQueue.length}`);
        if (!this.isPlayingAudio) {
            this.playNextAudioSegment();
        }
    }

    private playNextAudioSegment(): void {
        if (this.audioQueue.length > 0 && !this.isPlayingAudio) {
            this.isPlayingAudio = true;
            const currentSegment = this.audioQueue.shift()!;
            this.currentPlayingAudio = currentSegment.audio;
            
            showNeuroCaption(currentSegment.text);

            this.currentPlayingAudio.play().catch(e => {
                console.error("Error playing audio segment:", e);
                this.isPlayingAudio = false;
                this.currentPlayingAudio = null;
                this.playNextAudioSegment();
            });

            this.currentPlayingAudio.addEventListener('ended', () => {
                this.isPlayingAudio = false;
                this.currentPlayingAudio = null;
                this.playNextAudioSegment();
            }, { once: true });
        } else if (this.audioQueue.length === 0 && this.allSegmentsReceived) {
            console.log("Neuro's full audio response played.");
            hideNeuroCaption();
        }
    }
    
    public setAllSegmentsReceived(): void {
        this.allSegmentsReceived = true;
        if (this.audioQueue.length === 0 && !this.isPlayingAudio) {
            hideNeuroCaption();
        }
    }

    public stopAllAudio(): void {
        if (this.currentPlayingAudio) {
            this.currentPlayingAudio.pause();
            this.currentPlayingAudio.currentTime = 0;
            this.currentPlayingAudio = null;
        }
        this.audioQueue.length = 0;
        this.isPlayingAudio = false;
        this.allSegmentsReceived = false;
        hideNeuroCaption();
        console.log("Neuro audio playback stopped, queue cleared.");
    }
}