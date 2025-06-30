# backend/audio_synthesis.py
import os
import base64
import azure.cognitiveservices.speech as speechsdk
import asyncio

# 从 config 模块导入 Azure TTS 相关配置
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_TTS_VOICE_NAME, AZURE_TTS_VOICE_PITCH

async def synthesize_audio_segment(text: str, voice_name: str = AZURE_TTS_VOICE_NAME, pitch: float = AZURE_TTS_VOICE_PITCH) -> tuple[str, float]:
    """
    使用 Azure TTS 合成音频。
    返回 Base64 编码的音频字符串和音频时长（秒）。
    """
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech Key 或 Region 未配置，无法进行 TTS 合成。")

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
        
        # 获取音频时长（Azure SDK v2 返回 timedelta 对象）
        audio_duration_timedelta = result.audio_duration
        # 从 timedelta 对象中获取总秒数（浮点数）
        audio_duration_sec = audio_duration_timedelta.total_seconds()
        
        print(f"TTS 合成完成，文本: '{text[:50]}...', 时长: {audio_duration_sec:.2f} 秒")
        return encoded_audio, audio_duration_sec
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = f"语音合成取消: {cancellation_details.reason}。"
        if cancellation_details.error_details:
            error_message += f" 详情: {cancellation_details.error_details}"
        raise Exception(error_message)
    else:
        error_details = result.error_details if hasattr(result, 'error_details') else 'N/A'
        raise Exception(f"语音合成失败: {result.reason}。错误详情: {error_details}")