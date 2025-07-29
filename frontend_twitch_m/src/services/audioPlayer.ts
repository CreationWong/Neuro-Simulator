// src/services/audioPlayer.ts

import { showNeuroCaption, hideNeuroCaption, startCaptionTimeout } from '../ui/neuroCaption';

interface AudioSegment {
    text: string;
    audio: HTMLAudioElement;
    duration: number; // <-- 新增：保存每个片段的时长
}

export class AudioPlayer {
    private audioQueue: AudioSegment[] = [];
    private isPlayingAudio: boolean = false;
    private currentPlayingAudio: HTMLAudioElement | null = null;
    private allSegmentsReceived: boolean = false;
    private errorSound: HTMLAudioElement; 
    private lastSegmentEnd: boolean = true;

    constructor() {
        this.errorSound = new Audio('/error.mp3'); 
        console.log("AudioPlayer initialized.");
    }

    public playErrorSound(): void {
        this.stopAllAudio(); 
        console.log("Playing dedicated error sound...");
        this.errorSound.play().catch(e => {
            console.error("Error playing dedicated error sound:", e);
        });
    }

    /**
     * 新增：添加音频片段时传入 duration
     */
    public addAudioSegment(text: string, audioBase64: string, duration: number): void { // <-- 增加 duration 参数
        // 新段落开始时，先隐藏字幕
        if (this.lastSegmentEnd) {
            hideNeuroCaption();
        }
        this.lastSegmentEnd = false;
        const audio = new Audio('data:audio/mp3;base64,' + audioBase64);
        this.audioQueue.push({ text, audio, duration }); // <-- 存储 duration
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
            
            // --- 核心修改：调用 showNeuroCaption 时传入时长 ---
            showNeuroCaption(currentSegment.text, currentSegment.duration);

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
            console.log("Neuro's full audio response played. Starting caption timeout.");
            startCaptionTimeout();
        }
    }
    
    public setAllSegmentsReceived(): void {
        this.allSegmentsReceived = true;
        this.lastSegmentEnd = true;
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
        hideNeuroCaption(); // 强制隐藏字幕
        console.log("Neuro audio playback stopped, queue cleared.");
    }
}