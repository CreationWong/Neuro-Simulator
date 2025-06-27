// src/main.ts

// Type declarations for Node.js timers, to satisfy TypeScript in browser context
declare var setTimeout: typeof import('timers').setTimeout;
declare var clearTimeout: typeof import('timers').clearTimeout;

const BACKEND_BASE_URL = 'http://127.0.0.1:8000';
const MY_USERNAME = "Files_Transfer"; // Your username

// Get HTML elements
const chatInput = document.getElementById('chat-input') as HTMLInputElement;
const sendButton = document.getElementById('send-button') as HTMLButtonElement;
const chatMessages = document.getElementById('chat-messages') as HTMLDivElement;
const neuroCaption = document.getElementById('neuro-caption') as HTMLDivElement;
const resetButton = document.getElementById('reset-button') as HTMLAnchorElement;

// Audio playback queue and state
interface AudioSegment {
    text: string;
    audio: HTMLAudioElement;
}

const audioQueue: AudioSegment[] = [];
let isPlayingAudio = false;
let allSegmentsReceived = false; // Indicates if all segments for current Neuro response are received from backend

// --- Helper Functions ---
function getRandomChatColor(): string {
    const colors = [
        '#FF0000', '#00FF00', '#0000FF', '#00FFFF', '#FF00FF',
        '#FF4500', '#ADFF2F', '#1E90FF', '#FFD700', '#8A2BE2', '#00CED1',
        '#FF69B4', '#DA70D6', '#BA55D3', '#87CEEB', '#32CD32', '#CD853F'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Simplified appendChatMessage - all messages (AI audience or user) are treated as chat
function appendChatMessage(username: string, text: string) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    if (username === MY_USERNAME) {
        messageDiv.classList.add('user-sent-message'); 
    } else if (username === "System") {
        messageDiv.classList.add('system-message');
    }
    else { // AI audience messages
        messageDiv.classList.add('audience-ai-message');
    }

    const usernameSpan = document.createElement('span');
    usernameSpan.className = 'username';
    usernameSpan.textContent = username + ': ';
    usernameSpan.style.color = (username === MY_USERNAME) ? '#9147FF' : getRandomChatColor();

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    textSpan.style.color = 'var(--twitch-text-color)';

    messageDiv.appendChild(usernameSpan);
    messageDiv.appendChild(textSpan);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
}

function showNeuroCaption(text: string) {
    neuroCaption.textContent = text;
    neuroCaption.classList.add('show');
}

function playNextAudioSegment() {
    if (audioQueue.length > 0 && !isPlayingAudio) {
        isPlayingAudio = true;
        const currentSegment = audioQueue.shift()!;
        
        showNeuroCaption(currentSegment.text);

        currentSegment.audio.play().then(() => {
            // Audio playback successfully started
        }).catch(e => {
            console.error("Error playing audio:", e);
            isPlayingAudio = false;
            playNextAudioSegment();
        });

        currentSegment.audio.addEventListener('ended', () => {
            isPlayingAudio = false;
            playNextAudioSegment();
        }, { once: true });
    } else if (audioQueue.length === 0 && allSegmentsReceived) {
        // All audio segments have been played AND all segments have been received from backend
        console.log("All Neuro audio segments played and received. Signaling backend.");
        // --- NEW: Signal backend that TTS is finished ---
        if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
            neuroWs.send(JSON.stringify({ type: "tts_finished" }));
        }
        // Caption remains visible
    }
}

async function playVedalErrorSpeech(errorMessage: string = "Someone tell Vedal there is a problem with my AI.") {
    console.error("Attempting to play error speech:", errorMessage);
    try {
        const response = await fetch(`${BACKEND_BASE_URL}/synthesize_error_speech`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: errorMessage, voice_name: "en-US-AshleyNeural", pitch: 1.25 }),
        });

        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`Failed to get error speech from backend: ${response.status} - ${errorBody}`);
            return;
        }

        const data = await response.json();
        if (data.audio_base64) {
            const errorAudio = new Audio('data:audio/mp3;base64,' + data.audio_base64);
            errorAudio.play().catch(e => console.error("Error playing fetched error audio:", e));
        } else {
            console.warn("No audio_base64 received for error speech.");
        }
    } catch (error) {
        console.error("Error making HTTP request for error speech:", error);
    }
}

// --- WebSocket Connections ---
let neuroWs: WebSocket | null = null;
let audienceWs: WebSocket | null = null;

function connectNeuroWebSocket() {
    if (neuroWs && (neuroWs.readyState === WebSocket.OPEN || neuroWs.readyState === WebSocket.CONNECTING)) {
        console.log("Neuro WebSocket already connected or connecting.");
        return;
    }

    neuroWs = new WebSocket(`${BACKEND_BASE_URL.replace('http', 'ws')}/ws/chat_stream`);

    neuroWs.onopen = (event) => {
        console.log("Neuro WebSocket opened:", event);
        sendButton.disabled = false;
        chatInput.disabled = false;
        
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';
    };

    neuroWs.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log("Received Neuro WS message:", message);

        if (message.type === "segment") {
            const audio = new Audio('data:audio/mp3;base64,' + message.audio_base64);
            audioQueue.push({ text: message.text, audio: audio });
            if (!isPlayingAudio) {
                playNextAudioSegment();
            }
        } else if (message.type === "end") {
            allSegmentsReceived = true;
            // Now, we don't just log, we check if all audio has played as well
            if (audioQueue.length === 0 && !isPlayingAudio) {
                // All segments received from backend AND all played
                console.log("Neuro's response ended (all segments received and played). Signaling backend.");
                if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
                    neuroWs.send(JSON.stringify({ type: "tts_finished" }));
                }
            } else {
                console.log("Neuro's response segments received, waiting for audio playback to finish...");
            }
            sendButton.disabled = false;
            chatInput.disabled = false;
        } else if (message.type === "error") {
            console.error("Neuro Backend error received:", message.message);
            showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
            playVedalErrorSpeech();
            
            allSegmentsReceived = true; // Even on error, assume "finished" for this turn
            sendButton.disabled = false;
            chatInput.disabled = false;
            audioQueue.length = 0;
            isPlayingAudio = false;
            // Signal backend that Neuro is "finished" talking (due to error)
            if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
                neuroWs.send(JSON.stringify({ type: "tts_finished" }));
            }
        }
    };

    neuroWs.onclose = (event) => {
        console.log("Neuro WebSocket closed:", event.code, event.reason);
        sendButton.disabled = true;
        chatInput.disabled = true;
        isPlayingAudio = false;
        allSegmentsReceived = false;
        audioQueue.length = 0;
        
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';
        setTimeout(connectNeuroWebSocket, 3000);
    };

    neuroWs.onerror = (error) => {
        console.error("Neuro WebSocket error:", error);
        
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';
        
        allSegmentsReceived = true;
        sendButton.disabled = false;
        chatInput.disabled = false;
        // Signal backend on error to prevent being stuck
        if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
            neuroWs.send(JSON.stringify({ type: "tts_finished" }));
        }
    };
}

function connectAudienceWebSocket() {
    if (audienceWs && (audienceWs.readyState === WebSocket.OPEN || audienceWs.readyState === WebSocket.CONNECTING)) {
        console.log("Audience WebSocket already connected or connecting.");
        return;
    }

    audienceWs = new WebSocket(`${BACKEND_BASE_URL.replace('http', 'ws')}/ws/audience_chat_display`);

    audienceWs.onopen = (event) => {
        console.log("Audience WebSocket opened:", event);
        // Initial welcome message handled by backend now
    };

    audienceWs.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "audience_chat") {
            appendChatMessage(message.username, message.text); 
        }
    };

    audienceWs.onclose = (event) => {
        console.log("Audience WebSocket closed:", event.code, event.reason);
        setTimeout(connectAudienceWebSocket, 3000); 
    };

    audienceWs.onerror = (error) => {
        console.error("Audience WebSocket error:", error);
    };
}


// Send message function
async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (!userMessage) return;

    if (neuroWs && neuroWs.readyState === WebSocket.OPEN) {
        try {
            sendButton.disabled = true;
            chatInput.disabled = true;

            // Send user message with type 'user_message'
            await neuroWs.send(JSON.stringify({ type: "user_message", message: userMessage, username: MY_USERNAME }));
            console.log(`User message '${userMessage}' sent via Neuro WebSocket.`);

        }
        catch (error) {
            console.error('Error sending message to Neuro WebSocket:', error);
            showNeuroCaption("There was an issue sending your message.");
            playVedalErrorSpeech();
            sendButton.disabled = false;
            chatInput.disabled = false;
        }
    } else {
        console.warn("Neuro WebSocket is not open. Trying to reconnect...");
        connectNeuroWebSocket();
        showNeuroCaption("Connection lost. Retrying...");
        playVedalErrorSpeech("Connection to Neuro-Sama's backend was lost. Retrying.");
        sendButton.disabled = false;
        chatInput.disabled = false;
    }
    chatInput.value = '';
}

// Reset button event listener
resetButton.addEventListener('click', async (event) => {
    event.preventDefault();

    console.log("Reset button clicked. Attempting to reset Neuro's memory and clear chat history.");
    
    sendButton.disabled = true;
    chatInput.disabled = true;
    
    try {
        const response = await fetch(`${BACKEND_BASE_URL}/reset_agent_messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Reset API error: ${response.status} ${response.statusText} - ${errorText}`);
        }

        console.log("Neuro Agent messages reset successfully on backend.");
        chatMessages.innerHTML = '';
        appendChatMessage("System", 'Chat history and AI memory have been reset. Welcome to a new conversation!');
        
        audioQueue.length = 0;
        isPlayingAudio = false;
        
        neuroCaption.classList.remove('show');
        neuroCaption.textContent = '';

        sendButton.disabled = false;
        chatInput.disabled = false;

    } catch (error) {
        console.error('Error resetting conversation:', error);
        showNeuroCaption("Someone tell Vedal there is a problem with my AI.");
        playVedalErrorSpeech();
        
        sendButton.disabled = false;
        chatInput.disabled = false;
    }
});


// Add event listeners
sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// On page load, connect WebSockets
document.addEventListener('DOMContentLoaded', () => {
    sendButton.disabled = true;
    chatInput.disabled = true;
    
    connectNeuroWebSocket();
    connectAudienceWebSocket();
});
