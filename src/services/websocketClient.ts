// src/services/websocketClient.ts

import { 
    WebSocketMessage, 
    StreamStateSyncMessage, 
    NeuroSpeechSegmentMessage, 
    ChatMessage, 
    BackendErrorMessage,
    UserInputMessage,
    TTSFinishedMessage,
    NeuroAvatarStageUpdateMessage
} from '../types/common';

// 使用交叉类型 (&) 来解决索引签名和特定属性不兼容的问题
type MessageHandlers = {
    [key: string]: (message: any) => void; // 使用 any 来放宽索引签名的限制
} & {
    // 为特定的消息类型定义更具体的处理器
    stream_state_sync?: (message: StreamStateSyncMessage) => void;
    neuro_speech_segment?: (message: NeuroSpeechSegmentMessage) => void;
    chat_message?: (message: ChatMessage) => void;
    error?: (message: BackendErrorMessage) => void;
};

interface WebSocketClientOptions {
    url: string;
    onMessage?: (message: WebSocketMessage) => void;
    messageHandlers?: MessageHandlers;
    onOpen?: () => void;
    onClose?: (event: CloseEvent) => void;
    onError?: (event: Event) => void;
    autoReconnect?: boolean;
    reconnectInterval?: number;
}

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private readonly url: string;
    private readonly onMessage?: (message: WebSocketMessage) => void;
    private readonly messageHandlers: MessageHandlers;
    private readonly onOpen?: () => void;
    private readonly onClose?: (event: CloseEvent) => void;
    private readonly onError?: (event: Event) => void;
    private readonly autoReconnect: boolean;
    private readonly reconnectInterval: number;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 10;
    private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    constructor(options: WebSocketClientOptions) {
        this.url = options.url;
        this.onMessage = options.onMessage;
        this.messageHandlers = options.messageHandlers || {};
        this.onOpen = options.onOpen;
        this.onClose = options.onClose;
        this.onError = options.onError;
        this.autoReconnect = options.autoReconnect ?? true;
        this.reconnectInterval = options.reconnectInterval ?? 3000;
    }

    public connect(): void {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            console.warn(`WebSocket for ${this.url} is already connected or connecting.`);
            return;
        }

        console.log(`Connecting to WebSocket: ${this.url}`);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log(`WebSocket connected: ${this.url}`);
            this.reconnectAttempts = 0;
            if (this.reconnectTimeout) {
                clearTimeout(this.reconnectTimeout);
                this.reconnectTimeout = null;
            }
            if (this.onOpen) {
                this.onOpen();
            }
        };

        this.ws.onmessage = (event: MessageEvent) => {
            try {
                const message: WebSocketMessage = JSON.parse(event.data);
                if (this.onMessage) {
                    this.onMessage(message);
                }
                if (message.type && this.messageHandlers[message.type]) {
                    this.messageHandlers[message.type](message);
                }
            } catch (error) {
                console.error(`Error parsing message from ${this.url}:`, error, event.data);
            }
        };

        this.ws.onclose = (event: CloseEvent) => {
            console.warn(`WebSocket closed: ${this.url}. Code: ${event.code}, Reason: ${event.reason}`);
            this.ws = null;
            if (this.onClose) {
                this.onClose(event);
            }
            if (this.autoReconnect && event.code !== 1000) {
                this.tryReconnect();
            }
        };

        this.ws.onerror = (event: Event) => {
            console.error(`WebSocket error: ${this.url}`, event);
            if (this.onError) {
                this.onError(event);
            }
        };
    }

    private tryReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect to ${this.url} in ${this.reconnectInterval / 1000} seconds (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            this.reconnectTimeout = setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.error(`Max reconnect attempts (${this.maxReconnectAttempts}) reached for ${this.url}. Giving up.`);
        }
    }

    public send(message: UserInputMessage | TTSFinishedMessage | NeuroAvatarStageUpdateMessage): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(message));
            } catch (error) {
                console.error(`Error sending message to ${this.url}:`, error);
            }
        } else {
            console.warn(`WebSocket for ${this.url} is not open. Message not sent:`, message);
        }
    }

    public disconnect(): void {
        if (this.ws) {
            console.log(`Disconnecting WebSocket: ${this.url}`);
            this.ws.close(1000, "Client initiated disconnect");
            if (this.reconnectTimeout) {
                clearTimeout(this.reconnectTimeout);
                this.reconnectTimeout = null;
            }
            this.ws = null;
        }
    }

    public isConnected(): boolean {
        return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    }
}