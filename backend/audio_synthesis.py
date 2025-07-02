# backend/audio_synthesis.py
import os
import base64
import html
import azure.cognitiveservices.speech as speechsdk
import asyncio

from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_TTS_VOICE_NAME, AZURE_TTS_VOICE_PITCH

async def synthesize_audio_segment(text: str, voice_name: str = AZURE_TTS_VOICE_NAME, pitch: float = AZURE_TTS_VOICE_PITCH) -> tuple[str, float]:
    """
    使用 Azure TTS 合成音频。
    返回 Base64 编码的音频字符串和音频时长（秒）。
    """
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        # 这是一个配置错误，应该作为异常抛出
        raise ValueError("Azure Speech Key 或 Region 未在 .env 文件中配置。")

    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

    pitch_percent = int((pitch - 1.0) * 100)
    pitch_ssml_value = f"+{pitch_percent}%" if pitch_percent >= 0 else f"{pitch_percent}%"
    
    # 清理文本，防止特殊字符破坏 SSML 结构
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

    # 使用 audio_config=None 将音频输出到内存
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    # 在一个单独的线程中运行同步的 SDK 调用，以避免阻塞 asyncio 事件循环
    def _perform_synthesis_sync():
        return synthesizer.speak_ssml_async(ssml_string).get()

    try:
        result = await asyncio.to_thread(_perform_synthesis_sync)

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            audio_duration_sec = result.audio_duration.total_seconds()
            
            # 保留这条成功的日志，有助于追踪流程
            print(f"TTS 合成完成: '{text[:30]}...' (时长: {audio_duration_sec:.2f}s)")
            return encoded_audio, audio_duration_sec
        
        # --- 关键的错误处理 ---
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_message = f"TTS 合成被取消 (原因: {cancellation_details.reason})。文本: '{text}'"
            if cancellation_details.error_details:
                # 包含 429 (配额用尽) 等重要信息
                error_message += f" | 详情: {cancellation_details.error_details}"
            print(f"错误: {error_message}")
            raise Exception(error_message)
        else:
            error_message = f"TTS 合成失败 (原因: {result.reason})。文本: '{text}'"
            print(f"错误: {error_message}")
            raise Exception(error_message)

    except Exception as e:
        # 捕获其他网络或SDK内部异常
        print(f"错误: 在调用 Azure TTS SDK 时发生异常: {e}")
        raise # 重新抛出异常，以便上层逻辑(asyncio.gather)能捕获它