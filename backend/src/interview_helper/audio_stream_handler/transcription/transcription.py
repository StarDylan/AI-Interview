from interview_helper.audio_stream_handler.transcription.azure_transcriber import (
    azure_transcribe_audio_consumer,
    azure_transcribe_stop,
)
from interview_helper.audio_stream_handler.transcription.vosk_transcriber import (
    vosk_close_transcriber,
    vosk_transcribe_audio_consumer,
)
from interview_helper.context_manager.session_context_manager import (
    AsyncAudioConsumer,
    AsyncAudioConsumerFinalize,
)

vosk_transcriber_consumer_pair: tuple[
    AsyncAudioConsumer, AsyncAudioConsumerFinalize
] = (
    vosk_transcribe_audio_consumer,
    vosk_close_transcriber,
)
azure_transcriber_consumer_pair: tuple[
    AsyncAudioConsumer, AsyncAudioConsumerFinalize
] = (azure_transcribe_audio_consumer, azure_transcribe_stop)
