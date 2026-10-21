"""Speech to text, lazily and locally.

The page decodes and resamples the recording itself and posts 16 kHz mono float32, so no
media decoder is needed here: faster-whisper takes a numpy array straight. That also
dodges a version clash between faster-whisper and PyAV, which only matters when a file
has to be decoded.

faster-whisper runs on the CPU by default: ctranslate2's CUDA path needs cuDNN 9 on the
PATH, which a bare Python install does not have. `ASR_DEVICE=cuda` opts in when it does.
"""

import os

import numpy as np

MODEL = os.getenv("ASR_MODEL", "small.en")
DEVICE = os.getenv("ASR_DEVICE", "cpu")
COMPUTE = os.getenv("ASR_COMPUTE", "int8")

_model = None


def load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE)
    return _model


def transcribe(pcm: bytes) -> str:
    """16 kHz mono float32 in, transcript out. Empty string when nothing was said."""
    audio = np.frombuffer(pcm, dtype="<f4").astype(np.float32)
    if audio.size < 1600:
        return ""
    segments, _ = load().transcribe(audio, beam_size=1, language="en", vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()
