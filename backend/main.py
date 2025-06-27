import os
import base64
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage
import asyncio
import re
import json
import traceback
from collections import deque
import random

from google import genai
from google.genai import types 
from starlette.websockets import WebSocketState # Import WebSocketState for correct enum comparison

# 1. Load environment variables
load_dotenv()

LETTA_API_TOKEN = os.getenv("LETTA_API_TOKEN")
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL")
NEURO_AGENT_ID = os.getenv("AGENT_ID") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
AUDIENCE_MODEL_NAME = os.getenv("AUDIENCE_MODEL_NAME", "gemini-2.5-flash-lite-preview-06-17") 

if not LETTA_API_TOKEN:
    print("Warning: LETTA_API_TOKEN not found in .env file. Using a dummy token for letta_client initialization.")
    LETTA_API_TOKEN = "dummy_token"

if not LETTA_BASE_URL:
    raise ValueError("LETTA_BASE_URL not found in .env file. Please specify your self-hosted Letta server URL (e.g., http://localhost:8283).")

if not NEURO_AGENT_ID:
    raise ValueError("NEURO_AGENT_ID not found in .env file. Please provide the ID of your pre-existing Neuro Letta Agent.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file. Required for Audience LLM.")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    print("Warning: AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not found in .env. Azure TTS/STT will not be functional.")


# 2. Initialize FastAPI App
app = FastAPI()

# Configure CORS middleware
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Initialize Letta client for Neuro and Gemini Client for Audience
letta_client = Letta(token=LETTA_API_TOKEN, base_url=LETTA_BASE_URL)
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# --- Global Queues and Events ---
audience_chat_buffer = deque(maxlen=500) 
neuro_input_queue = deque(maxlen=200) 

audience_display_websockets: list[WebSocket] = []
neuro_tts_websocket: WebSocket | None = None

neuro_tts_ready_event = asyncio.Event()
# neuro_tts_ready_event's state will be managed by _trigger_neuro_response_flow
# and frontend's 'tts_finished' signal.

# --- LLM Prompts (English) ---
NEURO_AGENT_SYSTEM_PROMPT = """You are Neuro-Sama, an AI VTuber. You are intelligent, sometimes quirky, and observant.
Your primary role is to host a live stream, interact with your audience, and maintain an engaging personality.
You will receive messages from the stream chat. These messages can be direct questions to you, comments about your stream, or general banter among viewers.
Selectively respond to or acknowledge a few recent chat messages in your replies. You do not need to reply to every single message.
Maintain your VTuber persona. Do not explicitly mention 'AI' or 'LLM' unless specifically asked.
Keep your responses concise and natural for a live stream.
"""

AUDIENCE_LLM_PROMPT = """You are a Twitch live stream viewer. Generate short, realistic chat messages as if you are watching a stream.
Your messages should be varied: questions, comments about the streamer (Neuro-Sama), emotes, general banter, or reactions to what Neuro might be saying.
Do NOT act as the streamer (Neuro-Sama). Do NOT generate full conversations or detailed replies.
Generate around 10 distinct chat messages. Each message should be prefixed with a fictional username, like 'username: message text'.
Examples:
KappaKing: LUL
ChatterBox: Is Neuro talking about the weather again?
EmoteSpammer: pog pog pog
QuestionMark: How are you doing today, Neuro?
StreamFan: Neuro-Sama you are so cool!
"""

# --- Initial System Prompt for Neuro's first turn ---
INITIAL_NEURO_STARTUP_MESSAGE = {"username": "System", "text": "Welcome to the stream, Neuro-Sama! How are you doing today? Your audience is excited to chat with you."}

@app.on_event("startup")
async def startup_event():
    """On app startup, confirm Letta Agent existence and start background tasks."""
    global NEURO_AGENT_ID

    print(f"Attempting to retrieve Neuro Letta Agent with ID: {NEURO_AGENT_ID}")
    try:
        agent_data = letta_client.agents.retrieve(agent_id=NEURO_AGENT_ID)
        print(f"Successfully retrieved Agent details for ID: {agent_data.id}")
        llm_model_info = "N/A"
        if hasattr(agent_data, 'model') and agent_data.model:
            llm_model_info = agent_data.model
        elif agent_data.llm_config:
            if isinstance(agent_data.llm_config, LlmConfig):
                llm_config_dict = agent_data.llm_config.model_dump() if hasattr(agent_data.llm_config, 'model_dump') else agent_data.llm_config.__dict__
                llm_model_info = llm_config_dict.get('model_name') or llm_config_dict.get('name') or llm_config_dict.get('model')
            if not llm_model_info:
                llm_model_info = str(agent_data.llm_config)
        print(f"Neuro Agent Name: {agent_data.name}, LLM Model: {llm_model_info}")

    except Exception as e:
        print(f"Error: Could not retrieve Neuro Letta Agent with ID {NEURO_AGENT_ID}. Please ensure the ID is correct and your Letta server is running and accessible.")
        print(f"Details: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Neuro Agent {NEURO_AGENT_ID} cannot be found or accessed: {e}")
    
    # --- IMPORTANT: Reset Neuro's memory on every backend startup ---
    try:
        letta_client.agents.messages.reset(agent_id=NEURO_AGENT_ID)
        print(f"Neuro Agent {NEURO_AGENT_ID} memory reset on startup.")
    except Exception as e:
        print(f"Warning: Failed to reset Neuro Agent memory on startup: {e}. It might retain previous context.")

    # Start background tasks
    asyncio.create_task(generate_audience_chat_task())
    asyncio.create_task(neuro_processing_task())
    print("Background tasks 'generate_audience_chat_task' and 'neuro_processing_task' started.")


# --- Helper Functions ---
def split_text_into_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])(?<!Mr\.)(?<!Mrs\.)(?<!Dr\.)(?<!etc\.)\s+|$', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

async def synthesize_audio_segment(text: str, voice_name: str, pitch: float) -> str:
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech Key or Region not configured.")

    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

    pitch_percent = int((pitch - 1.0) * 100)
    pitch_ssml_value = f"+{pitch_percent}%" if pitch_percent >= 0 else f"{pitch_percent}%"

    ssml_string = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{voice_name}">
            <prosody pitch="{pitch_ssml_value}">
                {text}
            </prosody>
        </voice>
    </speak>
    """

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    def _perform_synthesis_sync():
        return synthesizer.speak_ssml_async(ssml_string).get()

    result = await asyncio.to_thread(_perform_synthesis_sync)

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_data = result.audio_data
        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
        return encoded_audio
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = f"Speech synthesis canceled: {cancellation_details.reason}."
        if cancellation_details.error_details:
            error_message += f" Details: {cancellation_details.error_details}"
        raise Exception(error_message)
    else:
        error_details = result.error_details if hasattr(result, 'error_details') else 'N/A'
        raise Exception(f"Speech synthesis failed: {result.reason}. Error details: {error_details}")


# --- HTTP Endpoints ---
class ErrorSpeechRequest(BaseModel):
    text: str
    voice_name: str = "en-US-AshleyNeural"
    pitch: float = 1.25

class ErrorSpeechResponse(BaseModel):
    audio_base64: str

@app.post("/synthesize_error_speech", response_model=ErrorSpeechResponse)
async def synthesize_error_speech_endpoint(request: ErrorSpeechRequest):
    """Synthesize speech for specific error messages via HTTP POST."""
    try:
        audio_base64 = await synthesize_audio_segment(
            text=request.text,
            voice_name=request.voice_name,
            pitch=request.pitch
        )
        return ErrorSpeechResponse(audio_base64=audio_base64)
    except Exception as e:
        print(f"Error synthesizing error speech: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to synthesize error speech: {e}")

@app.post("/reset_agent_messages", status_code=status.HTTP_200_OK)
async def reset_agent_messages():
    """Reset Neuro Letta Agent's message history and clear all chat queues."""
    print(f"Attempting to reset messages for Neuro Agent ID: {NEURO_AGENT_ID}")
    try:
        audience_chat_buffer.clear()
        neuro_input_queue.clear()
        letta_client.agents.messages.reset(agent_id=NEURO_AGENT_ID)
        print(f"Successfully reset messages for Neuro Agent ID: {NEURO_AGENT_ID} and cleared all chat queues.")
        
        # After reset, immediately add an initial prompt to kickstart Neuro
        neuro_input_queue.append(INITIAL_NEURO_STARTUP_MESSAGE)
        # Manually trigger Neuro processing flow since it's a reset
        _trigger_neuro_response_flow() 
        
        return {"message": f"Messages for Neuro agent {NEURO_AGENT_ID} reset successfully, and all chat queues cleared."}
    except Exception as e:
        print(f"Error resetting messages for Neuro Agent ID {NEURO_AGENT_ID}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to reset Neuro agent messages: {e}")

@app.get("/")
async def root():
    return {"message": "AI Streamer Backend is running and ready!"}

# --- Audience Chat Generation Background Task ---
async def generate_audience_chat_task():
    """
    Background task to continuously generate audience chat messages
    and add them to the audience_chat_buffer and neuro_input_queue.
    """
    username_pool = [
        "ChatterBox", "EmoteLord", "QuestionMark", "StreamFan", "PixelPundit",
        "CodeSage", "DataDiver", "ByteBard", "LogicLover", "AI_Enthusiast",
        "SynthWave", "CyberPunk", "NoSleepGang", "JustHere", "LurkMaster",
        "PogChamp", "KappaPride", "ModdedMind", "VirtualVoyager", "MatrixMind"
    ]
    
    chat_generation_interval = 4 # seconds (Changed to 4 seconds)
    llm_max_output_tokens = 500 # Adjust max tokens for ~10 chats (as per prompt)

    while True:
        try:
            response = await genai_client.aio.models.generate_content(
                model=AUDIENCE_MODEL_NAME,
                contents=[
                    {"role": "user", "parts": [{"text": AUDIENCE_LLM_PROMPT}]}
                ],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=llm_max_output_tokens 
                )
            )
            
            raw_chat_text = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        raw_chat_text += part.text

            parsed_chats = []
            for line in raw_chat_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    username_part, text_part = line.split(':', 1)
                    username = username_part.strip()
                    text = text_part.strip()
                    if username and text:
                        parsed_chats.append({"username": username, "text": text})
                elif line:
                    random_username = username_pool[len(audience_chat_buffer) % len(username_pool)]
                    parsed_chats.append({"username": random_username, "text": line})

            actual_generated_count = 0
            # Limit to a maximum of 10 chats to append, even if LLM generates more
            for chat in parsed_chats[:10]: # Limit to 10 chats
                audience_chat_buffer.append(chat)
                neuro_input_queue.append(chat)
                actual_generated_count += 1
            
            print(f"Generated {actual_generated_count} audience chats. Audience buffer size: {len(audience_chat_buffer)}. Neuro input queue size: {len(neuro_input_queue)}")

        except Exception as e:
            print(f"Error generating audience chat: {e}")
            traceback.print_exc()
        
        await asyncio.sleep(chat_generation_interval)

# --- Neuro Processing Background Task ---
# Helper function to trigger Neuro's processing flow
def _trigger_neuro_response_flow():
    """Sets the event to allow neuro_processing_task to proceed."""
    if not neuro_tts_ready_event.is_set():
        neuro_tts_ready_event.set()
        print("Triggered Neuro response flow (neuro_tts_ready_event set).")

async def neuro_processing_task():
    """
    Background task to continuously check neuro_input_queue,
    process messages with Neuro LLM when TTS is ready,
    and send responses to the frontend.
    """
    neuro_processing_interval = 0.5 # Check queue every 0.5 seconds
    chats_to_process_per_turn = 50 # Number of random chats to pull from queue for Neuro

    # Flag to ensure initial prompt is handled only once per task run
    _neuro_processing_task_first_run = True 

    while True:
        # Wait until Neuro's TTS is confirmed finished by frontend
        # This is the "car arrives at station" moment
        await neuro_tts_ready_event.wait() 
        
        # Clear the event immediately to prevent re-triggering until new TTS finishes
        # This is critical for the "wait until TTS is done" logic.
        neuro_tts_ready_event.clear() 

        # Give Neuro a small break/thinking time after speaking
        await asyncio.sleep(1) 

        # Add initial prompt if this is the first run of the task and queue is empty
        if _neuro_processing_task_first_run and not neuro_input_queue:
            neuro_input_queue.append(INITIAL_NEURO_STARTUP_MESSAGE)
            print("Added initial prompt to Neuro input queue at neuro_processing_task startup (first run).")
            _neuro_processing_task_first_run = False 
        
        # If the queue is empty, wait a bit more for messages to accumulate before next processing cycle.
        if not neuro_input_queue:
            print(f"Neuro input queue is empty. Waiting {neuro_processing_interval}s for more chats.")
            await asyncio.sleep(neuro_processing_interval)
            _trigger_neuro_response_flow() # Re-set event to allow next check
            continue
        
        # --- Prepare input for Neuro LLM ---
        current_queue_snapshot = list(neuro_input_queue)
        num_to_sample = min(chats_to_process_per_turn, len(current_queue_snapshot))
        
        if num_to_sample == 0:
            print("No chats to sample for Neuro despite queue having messages (min/max issue?). Waiting.")
            await asyncio.sleep(neuro_processing_interval)
            _trigger_neuro_response_flow() # Allow retry
            continue

        selected_chats_for_neuro = random.sample(current_queue_snapshot, num_to_sample)
        
        # Clear the queue for the next batch after processing
        # This assumes Neuro "consumes" these messages by reading them
        neuro_input_queue.clear() 

        injected_chat_text = ""
        if selected_chats_for_neuro:
            injected_chat_lines = [f"{chat['username']}: {chat['text']}" for chat in selected_chats_for_neuro]
            injected_chat_text = (
                "Recent stream chat messages:\n" + 
                "\n".join(injected_chat_lines) + 
                "\n\nPlease respond naturally, considering these messages and your role as a streamer."
            )

        neuro_llm_input_content = [TextContent(text=injected_chat_text)]
        
        print(f"Processing Neuro's input with {len(selected_chats_for_neuro)} messages from queue.")

        try:
            response = letta_client.agents.messages.create(
                agent_id=NEURO_AGENT_ID,
                messages=[
                    MessageCreate(
                        role="user", 
                        content=neuro_llm_input_content
                    )
                ]
            )

            ai_full_response_text = "I couldn't process that. Please try again."
            if response and response.messages:
                for msg in response.messages:
                    if isinstance(msg, AssistantMessage):
                        if hasattr(msg, 'content') and msg.content:
                            content_items = msg.content if isinstance(msg.content, list) else [msg.content]
                            for item in content_items:
                                if isinstance(item, TextContent) and item.text:
                                    ai_full_response_text = item.text
                                    break
                                elif isinstance(item, str):
                                    ai_full_response_text = item
                                    break
                        if ai_full_response_text != "I couldn't process that. Please try again.":
                            break
            
            print(f"Neuro's full response generated: '{ai_full_response_text}'")

            sentences = split_text_into_sentences(ai_full_response_text)
            if not sentences:
                if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                    await neuro_tts_websocket.send_json({"type": "end"})
                print("Neuro's response was empty.")
                _trigger_neuro_response_flow() # If response is empty, Neuro is ready for next input immediately
                continue

            for i, sentence in enumerate(sentences):
                if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        audio_base64 = await synthesize_audio_segment(
                            text=sentence,
                            voice_name="en-US-AshleyNeural",
                            pitch=1.25
                        )
                        await neuro_tts_websocket.send_json({
                            "type": "segment",
                            "segment_id": i,
                            "text": sentence,
                            "audio_base64": audio_base64
                        })
                    except Exception as e:
                        print(f"Error during TTS synthesis or sending segment '{sentence}': {e}")
                        if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                            await neuro_tts_websocket.send_json({
                                "type": "error",
                                "code": "TTS_SEGMENT_ERROR",
                                "message": f"TTS synthesis failed for segment: {e}",
                                "text_segment": sentence
                            })
                        break 
            
            if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                await neuro_tts_websocket.send_json({"type": "end"})
            print("Finished sending all segments for Neuro's response.")
            # Frontend will send 'tts_finished' signal when all audio has actually played.
            # So, we don't set neuro_tts_ready_event here.

        except Exception as e:
            traceback.print_exc()
            print(f"An error occurred in neuro_processing_task: {e}")
            if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await neuro_tts_websocket.send_json({"type": "error", "code": "NEURO_PROCESSING_ERROR", "message": f"Neuro processing error: {e}"})
                except RuntimeError as se:
                    print(f"Failed to send error message to Neuro client before closing: {se}")
            # Ensure event is set on error so processing doesn't get stuck
            _trigger_neuro_response_flow() 
        
        await asyncio.sleep(neuro_processing_interval)


# --- WebSocket Endpoints ---

@app.websocket("/ws/chat_stream")
async def websocket_neuro_chat(websocket: WebSocket):
    """
    Handles connection for Neuro's TTS stream (audio & caption) and
    receives user messages and TTS finished signals.
    """
    global neuro_tts_websocket
    
    if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
        print("Another Neuro TTS client tried to connect. Only one is allowed. Closing new connection.")
        await websocket.close(code=status.WS_1013_UNEXPECTED_CONDITION, reason="Only one Neuro TTS client allowed.")
        return

    neuro_tts_websocket = websocket
    await websocket.accept()
    print("Neuro TTS WebSocket client connected.")
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                parsed_data = json.loads(raw_data)
                message_type = parsed_data.get("type")

                if message_type == "user_message":
                    user_message_text = parsed_data.get("message", "").strip()
                    username = parsed_data.get("username", "User") 
                    if not user_message_text:
                        print("Received empty user message, ignoring.")
                        continue
                    user_chat_item = {"username": username, "text": user_message_text}
                    audience_chat_buffer.append(user_chat_item)
                    neuro_input_queue.append(user_chat_item)
                    print(f"User message '{user_message_text}' added to queues. Neuro input queue size: {len(neuro_input_queue)}. Audience buffer size: {len(audience_chat_buffer)}")
                
                elif message_type == "tts_finished":
                    # This signal means frontend has played all TTS audio
                    print("Received 'tts_finished' signal from frontend. Neuro is ready for next input.")
                    _trigger_neuro_response_flow() # Set the event to trigger neuro_processing_task

            except json.JSONDecodeError:
                print(f"Received non-JSON message: {raw_data}. Ignoring.")
            except Exception as e:
                print(f"Error processing received message in neuro_chat_ws: {e}")
                traceback.print_exc()

    except WebSocketDisconnect:
        print("Neuro TTS WebSocket client disconnected.")
    except Exception as e:
        traceback.print_exc()
        print(f"An unexpected Neuro TTS WebSocket error occurred: {e}")
    finally:
        neuro_tts_websocket = None
        # Ensure event is set if WS disconnects, to prevent background task from getting stuck
        _trigger_neuro_response_flow()
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED: 
                await websocket.close()
                print("Neuro TTS WebSocket connection closed.")
        except RuntimeError:
            pass


@app.websocket("/ws/audience_chat_display")
async def websocket_audience_chat_display(websocket: WebSocket):
    """
    Handles streaming all chat messages (AI generated + user) to the frontend for display.
    """
    await websocket.accept()
    audience_display_websockets.append(websocket)
    print("Audience Chat Display WebSocket client connected.")

    chat_send_interval = 0.5 # seconds
    num_chats_to_send_per_interval = 3 

    try:
        # Send initial backlog of chats
        initial_backlog_limit = 50 
        initial_chats_to_send = list(audience_chat_buffer)[-initial_backlog_limit:]
        for chat in initial_chats_to_send:
            try:
                if websocket.client_state == WebSocketState.CONNECTED: 
                    await websocket.send_json({
                        "type": "audience_chat",
                        "username": chat["username"],
                        "text": chat["text"]
                    })
                    await asyncio.sleep(0.01) 
                else:
                    print(f"Skipping initial backlog send, WebSocket not connected: {websocket.client_state}")
                    break
            except Exception as e:
                print(f"Error sending initial backlog chat: {e}")
                break 

        last_sent_index = len(audience_chat_buffer) # Start tracking from the end of initial backlog

        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                print("Audience Display WebSocket not connected, breaking loop.")
                break 

            if len(audience_chat_buffer) > last_sent_index:
                new_chats_to_send = list(audience_chat_buffer)[last_sent_index:]
                chats_chunk = new_chats_to_send[:num_chats_to_send_per_interval]
                
                for chat in chats_chunk:
                    try:
                        await websocket.send_json({
                            "type": "audience_chat",
                            "username": chat["username"],
                            "text": chat["text"]
                        })
                    except Exception as e:
                        print(f"Error sending audience chat: {e}")
                        break 
                last_sent_index += len(chats_chunk)
            
            await asyncio.sleep(chat_send_interval)

    except WebSocketDisconnect:
        print("Audience Chat Display WebSocket client disconnected.")
    except Exception as e:
        traceback.print_exc()
        print(f"An unexpected Audience Chat Display WebSocket error occurred: {e}")
    finally:
        if websocket in audience_display_websockets:
            audience_display_websockets.remove(websocket)
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED: 
                await websocket.close()
        except RuntimeError:
            pass