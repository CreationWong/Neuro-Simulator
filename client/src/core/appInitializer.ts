// src/core/appInitializer.ts

import { WebSocketClient } from '../services/websocketClient';
import { AudioPlayer } from '../services/audioPlayer';
import { VideoPlayer } from '../stream/videoPlayer';
import { NeuroAvatar } from '../stream/neuroAvatar';
import { ChatDisplay } from '../ui/chatDisplay';
import { showNeuroCaption, hideNeuroCaption } from '../ui/neuroCaption';
import { UserInput, MessagePayload } from '../ui/userInput';
import { LayoutManager } from './layoutManager';
import { StreamTimer } from '../ui/streamTimer';
import { ChatSidebar } from '../ui/chatSidebar';
import { LiveIndicator } from '../ui/liveIndicator';
import { StreamInfoDisplay } from '../ui/streamInfoDisplay';
import { WakeLockManager } from '../utils/wakeLockManager';
import { WebSocketMessage, ChatMessage, NeuroSpeechSegmentMessage, StreamMetadataMessage } from '../types/common';
import { SettingsModal, AppSettings } from '../ui/settingsModal';
import { MuteButton } from '../ui/muteButton';

export class AppInitializer {
    private wsClient: WebSocketClient;
    private audioPlayer: AudioPlayer;
    private videoPlayer: VideoPlayer;
    private neuroAvatar: NeuroAvatar;
    private chatDisplay: ChatDisplay;
    private userInput: UserInput;   
    private layoutManager: LayoutManager;
    private streamTimer: StreamTimer;
    private chatSidebar: ChatSidebar;
    private liveIndicator: LiveIndicator;
    private streamInfoDisplay: StreamInfoDisplay;
    private wakeLockManager: WakeLockManager;
    
    private settingsModal: SettingsModal;
    private currentSettings: AppSettings;
    private muteButton: MuteButton;
    private resizeObserver: ResizeObserver | null = null;

    private isStarted: boolean = false;
    private currentPhase: string = 'offline';

    constructor() {
        this.layoutManager = new LayoutManager();
        this.streamTimer = new StreamTimer();
        this.muteButton = new MuteButton();
        
        this.currentSettings = SettingsModal.getSettings();
        this.settingsModal = new SettingsModal((newSettings) => this.handleSettingsUpdate(newSettings));
        
        const backendWsUrl = this.currentSettings.backendUrl 
            ? `${this.currentSettings.backendUrl}/ws/stream`
            : '';

        const universalMessageHandler = (message: WebSocketMessage) => this.handleWebSocketMessage(message);
        
        this.wsClient = new WebSocketClient({
            url: backendWsUrl,
            autoReconnect: true,
            maxReconnectAttempts: this.currentSettings.reconnectAttempts,
            onMessage: universalMessageHandler,
            onOpen: () => this.goOnline(),
            onDisconnect: () => this.goOffline(),
        });

        this.audioPlayer = new AudioPlayer();
        this.videoPlayer = new VideoPlayer();
        this.neuroAvatar = new NeuroAvatar();
        this.chatDisplay = new ChatDisplay();
        this.userInput = new UserInput();
        this.userInput.onSendMessage((payload: MessagePayload) => this.sendUserMessage(payload));
        this.chatSidebar = new ChatSidebar();
        this.liveIndicator = new LiveIndicator();
        this.streamInfoDisplay = new StreamInfoDisplay();
        this.wakeLockManager = new WakeLockManager();
        
        this.setupSettingsModalTrigger();
        this.setupMuteButton();
    }

    public start(): void {
        if (this.isStarted) return;
        this.isStarted = true;

        this.layoutManager.start();
        this.goOffline(); // Start in offline state
        
        this.updateUiWithSettings();
        
        if (this.wsClient.getUrl()) {
            this.wsClient.connect();
        } else {
            console.warn("Backend URL is not configured. Opening settings modal.");
            this.settingsModal.open();
        }
    }

    private setupSettingsModalTrigger(): void {
        const trigger = document.querySelector('.nav-user-avatar-button');
        if (trigger) {
            trigger.addEventListener('click', () => {
                this.settingsModal.open();
            });
        }
    }

    private setupMuteButton(): void {
        const muteButtonElement = this.muteButton.create();
        if (muteButtonElement) {
            this.muteButton.show();
            const handleGlobalClick = () => {
                this.muteButton.unmute();
                document.removeEventListener('click', handleGlobalClick);
            };
            document.addEventListener('click', handleGlobalClick);
        }
    }

    public getMuteButton(): MuteButton {
        return this.muteButton;
    }

    public getAudioPlayer(): AudioPlayer {
        return this.audioPlayer;
    }

    private handleSettingsUpdate(newSettings: AppSettings): void {
        console.log("Settings updated. Re-initializing connection with new settings:", newSettings);
        this.currentSettings = newSettings;
        
        this.updateUiWithSettings();

        const newUrl = newSettings.backendUrl ? `${newSettings.backendUrl}/ws/stream` : '';
        this.wsClient.updateOptions({
            url: newUrl,
            maxReconnectAttempts: newSettings.reconnectAttempts,
        });

        this.wsClient.disconnect();
        
        setTimeout(() => {
            if(this.wsClient.getUrl()) {
                this.wsClient.connect();
            } else {
                console.warn("Cannot connect: Backend URL is empty after update.");
            }
        }, 500);
    }

    private updateUiWithSettings(): void {
        const userAvatars = document.querySelectorAll('.user-avatar-img') as NodeListOf<HTMLImageElement>;
        userAvatars.forEach(img => img.src = this.currentSettings.avatarDataUrl);
        console.log(`UI updated with username: ${this.currentSettings.username} and avatar.`);
    }

    private adjustOfflineLayout = () => {
        if (this.currentPhase !== 'offline') return;

        const videoPlayer = document.querySelector('.offline-video-player') as HTMLElement;
        const infoCard = document.querySelector('.offline-info-card') as HTMLElement;

        if (videoPlayer && infoCard) {
            const videoHeight = videoPlayer.offsetHeight;
            if (videoHeight > 0) {
                infoCard.style.height = `${videoHeight}px`;
                infoCard.style.width = `${videoHeight}px`;
            }
        }
    }

    private goOnline(): void {
        console.log("Entering ONLINE state.");
        this.updateUiWithSettings();

        // Stop observing and clear styles
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        const infoCard = document.querySelector('.offline-info-card') as HTMLElement;
        if (infoCard) {
            infoCard.style.height = '';
            infoCard.style.width = '';
        }

        document.getElementById('offline-content-container')?.classList.add('hidden');
        document.getElementById('stream-display-viewport')?.classList.remove('hidden');
        document.querySelector('.stream-info-details-row')?.classList.remove('hidden'); // Show details row
        document.getElementById('chat-sidebar')?.classList.remove('hidden');

        this.showStreamContent();
        this.chatDisplay.clearChat();
        this.liveIndicator.show();
        this.wakeLockManager.requestWakeLock();
    }

    private goOffline(): void {
        console.log("Entering OFFLINE state.");
        this.currentPhase = 'offline';

        // Show offline banner and hide online elements
        document.getElementById('offline-content-container')?.classList.remove('hidden');
        document.getElementById('stream-display-viewport')?.classList.add('hidden');
        document.querySelector('.stream-info-details-row')?.classList.add('hidden'); // Hide details row
        document.getElementById('chat-sidebar')?.classList.add('hidden');

        this.hideStreamContent();
        this.audioPlayer.stopAllAudio();
        this.videoPlayer.hide();
        this.neuroAvatar.setStage('hidden', true);
        hideNeuroCaption();
        this.streamTimer.stop();
        this.streamTimer.reset();
        this.chatDisplay.clearChat();
        this.liveIndicator.hide();
        this.wakeLockManager.releaseWakeLock();
        
        this.muteButton.show();
        const handleGlobalClick = () => {
            this.muteButton.unmute();
            document.removeEventListener('click', handleGlobalClick);
        };
        document.addEventListener('click', handleGlobalClick);

        // Adjust layout and set up observer
        setTimeout(() => {
            this.adjustOfflineLayout();
            const videoPlayer = document.querySelector('.offline-video-player');
            if (videoPlayer && !this.resizeObserver) {
                this.resizeObserver = new ResizeObserver(this.adjustOfflineLayout);
                this.resizeObserver.observe(videoPlayer);
            }
        }, 0);
    }

    private handleWebSocketMessage(message: WebSocketMessage): void {
        if (this.currentPhase === 'offline' && ['play_welcome_video', 'start_avatar_intro', 'enter_live_phase'].includes(message.type)) {
            console.log("Connection successful, transitioning from OFFLINE to active state.");
            this.goOnline(); // Use the new goOnline method
        }

        if (message.elapsed_time_sec !== undefined) {
            this.streamTimer.start(message.elapsed_time_sec);
        }

        switch (message.type) {
            case 'offline':
                this.goOffline();
                break;
            case 'update_stream_metadata':
                this.streamInfoDisplay.update(message as StreamMetadataMessage);
                break;
            case 'play_welcome_video':
                this.currentPhase = 'initializing';
                this.videoPlayer.showAndPlayVideo(parseFloat(message.progress as any));
                break;
            case 'start_avatar_intro':
                this.currentPhase = 'avatar_intro';
                this.videoPlayer.pauseAndMute();
                this.neuroAvatar.startIntroAnimation(() => { 
                    this.videoPlayer.hide(); 
                });
                break;
            case 'enter_live_phase':
                this.currentPhase = 'live';
                this.videoPlayer.hide();
                this.neuroAvatar.setStage('step2', true); 
                break;
            case 'neuro_is_speaking':
                break;
            case 'neuro_speech_segment':
                const segment = message as NeuroSpeechSegmentMessage;
                if (segment.is_end) {
                    this.audioPlayer.setAllSegmentsReceived(); 
                } else if (segment.audio_base64 && segment.text && typeof segment.duration === 'number') { 
                    this.audioPlayer.addAudioSegment(segment.text, segment.audio_base64, segment.duration);
                } else {
                    console.warn("Received neuro_speech_segment message with missing audio/text/duration:", segment);
                }
                break;
            case 'neuro_error_signal': 
                console.warn("Received neuro_error_signal from backend.");
                showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
                this.audioPlayer.playErrorSound();
                break;
            case 'chat_message':
                if (!this.chatSidebar.getIsCollapsed() || (message as ChatMessage).is_user_message) {
                   this.chatDisplay.appendChatMessage(message as ChatMessage);
                }
                break;
            case 'error':
                this.chatDisplay.appendChatMessage({ type: "chat_message", username: "System", text: `后端错误: ${(message as any).message}`, is_user_message: false });
                break;
        }
    }
    
    private sendUserMessage(payload: MessagePayload): void {
        const message = {
            username: this.currentSettings.username,
            ...payload
        };
        this.wsClient.send(message);
    }

    private showStreamContent(): void {
        const streamArea = document.getElementById('stream-display-area');
        if (streamArea) {
            streamArea.style.visibility = 'visible';
            streamArea.style.opacity = '1';
        }
    }

    private hideStreamContent(): void {
        const streamArea = document.getElementById('stream-display-area');
        if (streamArea) {
            streamArea.style.visibility = 'hidden';
            streamArea.style.opacity = '0';
        }
    }
}