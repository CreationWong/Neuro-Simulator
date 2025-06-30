// src/services/apiClient.ts

// 定义后端的基础 URL
const BACKEND_BASE_URL = 'http://127.0.0.1:8000'; 

/**
 * 封装与后端 HTTP API 交互的客户端。
 */
export class ApiClient {

    private baseUrl: string;

    constructor(baseUrl: string = BACKEND_BASE_URL) {
        this.baseUrl = baseUrl;
        console.log(`ApiClient initialized with base URL: ${this.baseUrl}`);
    }

    /**
     * 调用后端 API 重置 Neuro Agent 的记忆和直播状态。
     * @returns Promise<string> 成功消息或错误信息。
     */
    public async resetNeuroAgent(): Promise<string> {
        const url = `${this.baseUrl}/reset_agent_messages`;
        console.log(`Sending reset request to: ${url}`);
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                const errorBody = await response.text();
                const errorMessage = `Reset API Error: ${response.status} ${response.statusText} - ${errorBody}`;
                console.error(errorMessage);
                throw new Error(errorMessage);
            }

            const data = await response.json();
            console.log('Neuro Agent reset successfully:', data.message);
            return data.message;

        } catch (error) {
            console.error('Error during Neuro Agent reset:', error);
            throw error; // 重新抛出错误以便调用方处理
        }
    }

    /**
     * 调用后端 API 合成错误语音。
     * @param text 要合成的文本。
     * @param voiceName 语音名称 (可选)。
     * @param pitch 音高 (可选)。
     * @returns Promise<string> 音频的 Base64 编码字符串。
     */
    public async synthesizeErrorSpeech(text: string, voiceName?: string, pitch?: number): Promise<string> {
        const url = `${this.baseUrl}/synthesize_error_speech`;
        console.log(`Requesting error speech synthesis for text: "${text.substring(0, 50)}..."`);
        try {
            const body = { text, voice_name: voiceName, pitch };
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body),
            });

            if (!response.ok) {
                const errorBody = await response.text();
                const errorMessage = `Error Speech API Error: ${response.status} ${response.statusText} - ${errorBody}`;
                console.error(errorMessage);
                throw new Error(errorMessage);
            }

            const data = await response.json();
            if (data.audio_base64) {
                console.log('Error speech audio received.');
                return data.audio_base64;
            } else {
                const errorMessage = "No audio_base64 received from error speech synthesis.";
                console.warn(errorMessage);
                throw new Error(errorMessage);
            }

        } catch (error) {
            console.error('Error requesting error speech synthesis:', error);
            throw error;
        }
    }
}

// 导出 ApiClient 的一个单例实例，方便在其他模块中导入和使用
export const apiClient = new ApiClient();