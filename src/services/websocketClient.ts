// src/services/websocketClient.ts
import { WebSocketMessage } from '../types/common';

interface WebSocketClientOptions {
    url: string;
    onMessage?: (message: WebSocketMessage) => void;
    onOpen?: () => void;
    onClose?: (event: CloseEvent) => void;
    onError?: (event: Event) => void;
    onDisconnect?: () => void; // <-- 新增
    autoReconnect?: boolean;
    reconnectInterval?: number;
}

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private url: string;
    private readonly options: WebSocketClientOptions;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 10;
    private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    private explicitlyClosed: boolean = false;

    constructor(options: WebSocketClientOptions) {
        this.url = options.url;
        this.options = options;
    }

    public setUrl(newUrl: string): void {
        this.url = newUrl;
    }

    public getUrl(): string {
        return this.url;
    }

    public connect(): void {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            console.warn(`WebSocket for ${this.url} is already connected or connecting.`);
            return;
        }
        
        this.explicitlyClosed = false;
        console.log(`Connecting to WebSocket: ${this.url}`);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log(`WebSocket connected: ${this.url}`);
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
                this.options.onMessage?.(message);
            } catch (error) {
                console.error(`Error parsing message from ${this.url}:`, error, event.data);
            }
        };

        this.ws.onclose = (event: CloseEvent) => {
            console.warn(`WebSocket closed: ${this.url}. Code: ${event.code}, Reason: ${event.reason}`);
            this.ws = null;
            this.options.onClose?.(event);
            
            // 只有在不是明确调用 disconnect() 的情况下才触发 onDisconnect 和重连
            if (!this.explicitlyClosed) {
                this.options.onDisconnect?.(); // <-- 调用 onDisconnect 回调
                if (this.options.autoReconnect && event.code !== 1000) {
                    this.tryReconnect();
                }
            }
        };

        this.ws.onerror = (event: Event) => {
            console.error(`WebSocket error: ${this.url}`, event);
            this.options.onError?.(event);
        };
    }

    private tryReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect to ${this.url} in ${this.options.reconnectInterval ?? 3000 / 1000} seconds...`);
            this.reconnectTimeout = setTimeout(() => {
                this.connect();
            }, this.options.reconnectInterval ?? 3000);
        } else {
            console.error(`Max reconnect attempts reached for ${this.url}.`);
        }
    }

    public send(message: object): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn(`WebSocket for ${this.url} is not open. Message not sent.`);
        }
    }

    public disconnect(): void {
        this.explicitlyClosed = true;
        if (this.ws) {
            this.ws.close(1000, "Client initiated disconnect");
        }
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
        }
    }
}