# backend/audio_synthesis.py
import html
import base64
import azure.cognitiveservices.speech as speechsdk
import asyncio
from config import config_manager

async def synthesize_audio_segment(text: str, voice_name: str = None, pitch: float = None) -> tuple[str, float]:
    """
    使用 Azure TTS 合成音频。
    如果 voice_name 或 pitch 未提供，则使用配置中的默认值。
    返回 Base64 编码的音频字符串和音频时长（秒）。
    """
    # 使用 config_manager.settings 中的值
    azure_key = config_manager.settings.api_keys.azure_speech_key
    azure_region = config_manager.settings.api_keys.azure_speech_region
    
    if not azure_key or not azure_region:
        raise ValueError("Azure Speech Key 或 Region 未在配置中设置。")

    # 如果未传入参数，则使用配置的默认值
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
            print(f"TTS 合成完成: '{text[:30]}...' (时长: {audio_duration_sec:.2f}s)")
            return encoded_audio, audio_duration_sec
        else:
            cancellation_details = result.cancellation_details
            error_message = f"TTS 合成失败/取消 (原因: {cancellation_details.reason})。文本: '{text}'"
            if cancellation_details.error_details:
                error_message += f" | 详情: {cancellation_details.error_details}"
            print(f"错误: {error_message}")
            raise Exception(error_message)
    except Exception as e:
        print(f"错误: 在调用 Azure TTS SDK 时发生异常: {e}")
        raise