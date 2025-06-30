// src/services/apiClient.ts

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; 

export class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = BACKEND_BASE_URL) {
        this.baseUrl = baseUrl;
        console.log(`ApiClient initialized with base URL: ${this.baseUrl}`);
    }

    public async synthesizeErrorSpeech(text: string, voiceName?: string, pitch?: number): Promise<string> {
        const url = `${this.baseUrl}/synthesize_error_speech`;
        try {
            const body = { text, voice_name: voiceName, pitch };
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (!response.ok) {
                const errorBody = await response.text();
                throw new Error(`Error Speech API Error: ${response.status} - ${errorBody}`);
            }

            const data = await response.json();
            if (data.audio_base64) {
                return data.audio_base64;
            } else {
                throw new Error("No audio_base64 received from error speech synthesis.");
            }
        } catch (error) {
            console.error('Error requesting error speech synthesis:', error);
            throw error;
        }
    }
}

export const apiClient = new ApiClient();