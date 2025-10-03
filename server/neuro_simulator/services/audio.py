# neuro_simulator/services/audio.py
import asyncio
import base64
import html
import logging
import re

import azure.cognitiveservices.speech as speechsdk

from ..core.config import config_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

def _remove_emoji(text: str) -> str:
    """Removes emoji characters from a string."""
    if not text:
        return ""
    # This regex pattern covers a wide range of Unicode emoji characters.
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251" 
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r'', text).strip()

async def synthesize_audio_segment(text: str, tts_provider_id: str) -> tuple[str, float]:
    """
    Synthesizes audio using a configured TTS provider.
    Returns a Base64 encoded audio string and the audio duration in seconds.
    """
    # Clean emojis from the text before synthesis
    text = _remove_emoji(text)
    if not text:
        return "", 0.0

    # Find the specified TTS provider in the configuration
    provider_config = next((p for p in config_manager.settings.tts_providers if p.provider_id == tts_provider_id), None)

    if not provider_config:
        raise ValueError(f"TTS Provider with ID '{tts_provider_id}' not found in configuration.")

    # --- Dispatch based on provider type ---
    # Currently, only Azure is supported.
    if provider_config.provider_type == 'azure':
        if not provider_config.api_key or not provider_config.region:
            raise ValueError(f"Azure TTS provider '{provider_config.display_name}' is missing API key or region.")

        # Hardcoded voice and pitch as per design
        voice_name = "en-US-AshleyNeural"
        pitch = 1.25

        speech_config = speechsdk.SpeechConfig(subscription=provider_config.api_key, region=provider_config.region)
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

        pitch_percent = int((pitch - 1.0) * 100)
        pitch_ssml_value = f"+{pitch_percent}%" if pitch_percent >= 0 else f"{pitch_percent}%"
        
        escaped_text = html.escape(text)

        ssml_string = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice_name}">
                <prosody pitch="{pitch_ssml_value}">
                    {escaped_text}
                </prosody>
            </voice>
        </speak>
        """
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        def _perform_synthesis_sync():
            return synthesizer.speak_ssml_async(ssml_string).get()

        try:
            result = await asyncio.to_thread(_perform_synthesis_sync)

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                audio_duration_sec = result.audio_duration.total_seconds()
                logger.info(f"TTS synthesis completed: '{text[:30]}...' (Duration: {audio_duration_sec:.2f}s)")
                return encoded_audio, audio_duration_sec
            else:
                cancellation_details = result.cancellation_details
                error_message = f"TTS synthesis failed (Reason: {cancellation_details.reason}). Text: '{text}'"
                if cancellation_details.error_details:
                    error_message += f" | Details: {cancellation_details.error_details}"
                logger.error(error_message)
                raise Exception(error_message)
        except Exception as e:
            logger.error(f"An exception occurred during the Azure TTS SDK call: {e}", exc_info=True)
            raise
    else:
        raise NotImplementedError(f"TTS provider type '{provider_config.provider_type}' is not supported.")
