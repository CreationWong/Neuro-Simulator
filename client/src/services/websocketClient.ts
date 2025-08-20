// src/services/websocketClient.ts
import { WebSocketMessage } from '../types/common';
import { showSuperChatOverlay } from '../ui/chatDisplay';

// --- MODIFIED: Added maxReconnectAttempts to options ---
export interface WebSocketClientOptions {
    url: string;
    onMessage?: (message: WebSocketMessage) => void;
    onOpen?: () => void;
    onClose?: (event: CloseEvent) => void;
    onError?: (event: Event) => void;
    onDisconnect?: () => void;
    autoReconnect?: boolean;
    reconnectInterval?: number;
    maxReconnectAttempts?: number; // 新增：最大重连次数，-1为无限
}

export class WebSocketClient {
    private ws: WebSocket | null = null;
    // --- MODIFIED: url is now part of the options object ---
    private options: WebSocketClientOptions;
    private reconnectAttempts: number = 0;
    private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    private explicitlyClosed: boolean = false;

    constructor(options: WebSocketClientOptions) {
        // --- MODIFIED: Set default options and store the whole object ---
        this.options = {
            reconnectInterval: 3000,
            maxReconnectAttempts: 10, // 默认值
            ...options,
        };
    }

    public connect(): void {
        if (!this.options.url) {
            console.warn("WebSocket URL is not set. Connection aborted.");
            return;
        }
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            console.warn(`WebSocket for ${this.options.url} is already connected or connecting.`);
            return;
        }
        
        this.explicitlyClosed = false;
        console.log(`Connecting to WebSocket: ${this.options.url}`);
        this.ws = new WebSocket(this.options.url);

        this.ws.onopen = () => {
            console.log(`WebSocket connected: ${this.options.url}`);
            this.reconnectAttempts = 0;
            if (this.reconnectTimeout) {
                clearTimeout(this.reconnectTimeout);
                this.reconnectTimeout = null;
            }
            this.options.onOpen?.();
        };

        this.ws.onmessage = (event: MessageEvent) => {
            try {
                const message: WebSocketMessage = JSON.parse(event.data);
                if (message.type === 'processing_superchat') {
                    showSuperChatOverlay(message.data.username, message.data.text, message.data.sc_type);
                }
                this.options.onMessage?.(message);
            } catch (error) {
                console.error(`Error parsing message from ${this.options.url}:`, error, event.data);
            }
        };

        this.ws.onclose = (event: CloseEvent) => {
            console.warn(`WebSocket closed: ${this.options.url}. Code: ${event.code}, Reason: ${event.reason}`);
            this.ws = null;
            this.options.onClose?.(event);
            
            if (!this.explicitlyClosed) {
                this.options.onDisconnect?.();
                if (this.options.autoReconnect && event.code !== 1000) {
                    this.tryReconnect();
                }
            }
        };

        this.ws.onerror = (event: Event) => {
            console.error(`WebSocket error: ${this.options.url}`, event);
            this.options.onError?.(event);
        };
    }

    private tryReconnect(): void {
        // --- MODIFIED: Use configured maxReconnectAttempts and handle -1 ---
        const shouldRetry = this.options.maxReconnectAttempts === -1 || this.reconnectAttempts < this.options.maxReconnectAttempts!;
        
        if (shouldRetry) {
            this.reconnectAttempts++;
            const attemptInfo = this.options.maxReconnectAttempts === -1 
                ? `(attempt ${this.reconnectAttempts})` 
                : `(attempt ${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`;

            console.log(`Attempting to reconnect to ${this.options.url} in ${this.options.reconnectInterval! / 1000} seconds... ${attemptInfo}`);
            this.reconnectTimeout = setTimeout(() => {
                this.connect();
            }, this.options.reconnectInterval!);
        } else {
            console.error(`Max reconnect attempts reached for ${this.options.url}.`);
        }
    }

    public send(message: object): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn(`WebSocket for ${this.options.url} is not open. Message not sent.`);
        }
    }

    public disconnect(): void {
        this.explicitlyClosed = true;
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
        }
        if (this.ws) {
            this.ws.close(1000, "Client initiated disconnect");
        }
    }

    // --- NEW: A method to update options on the fly ---
    public updateOptions(newOptions: Partial<WebSocketClientOptions>): void {
        console.log("WebSocket client options updated:", newOptions);
        this.options = { ...this.options, ...newOptions };
    }
    
    // Kept for convenience, but updateOptions is more powerful
    public getUrl(): string {
        return this.options.url;
    }
}