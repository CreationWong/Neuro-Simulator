# neuro_simulator/services/audio.py
import asyncio
import base64
import html
import logging

import azure.cognitiveservices.speech as speechsdk

from ..core.config import config_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

async def synthesize_audio_segment(text: str, voice_name: str = None, pitch: float = None) -> tuple[str, float]:
    """
    Synthesizes audio using Azure TTS.
    Returns a Base64 encoded audio string and the audio duration in seconds.
    """
    azure_key = config_manager.settings.api_keys.azure_speech_key
    azure_region = config_manager.settings.api_keys.azure_speech_region
    
    if not azure_key or not azure_region:
        raise ValueError("Azure Speech Key or Region is not set in the configuration.")

    final_voice_name = voice_name if voice_name is not None else config_manager.settings.tts.voice_name
    final_pitch = pitch if pitch is not None else config_manager.settings.tts.voice_pitch

    speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

    pitch_percent = int((final_pitch - 1.0) * 100)
    pitch_ssml_value = f"+{pitch_percent}%" if pitch_percent >= 0 else f"{pitch_percent}%"
    
    escaped_text = html.escape(text)

    ssml_string = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{final_voice_name}">
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