import pytest

from app.errors import AppError
from app.speech import pcm_from_wav, text_from_response


def _wav(pcm: bytes, rate: int = 16000, channels: int = 1) -> bytes:
    block = channels * 2
    data_size = len(pcm)
    header = b"RIFF" + (36 + data_size).to_bytes(4, "little") + b"WAVE"
    fmt = (
        b"fmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + channels.to_bytes(2, "little")
        + rate.to_bytes(4, "little")
        + (rate * block).to_bytes(4, "little")
        + block.to_bytes(2, "little")
        + (16).to_bytes(2, "little")
    )
    return header + fmt + b"data" + data_size.to_bytes(4, "little") + pcm


def test_text_from_response_joins_transcripts() -> None:
    text = text_from_response(
        {"results": [{"alternatives": [{"transcript": "座っている 人", "confidence": 0.9}]}]}
    )
    assert text == "座っている 人"


def test_pcm_from_wav_reads_rate() -> None:
    pcm, rate = pcm_from_wav(_wav(b"\x01\x00\x02\x00", rate=16000))
    assert rate == 16000
    assert pcm == b"\x01\x00\x02\x00"


def test_stereo_keeps_left_channel() -> None:
    stereo = b"\x0a\x00\xff\x7f\x0b\x00\x00\x80"
    pcm, rate = pcm_from_wav(_wav(stereo, channels=2))
    assert rate == 16000
    assert pcm == b"\x0a\x00\x0b\x00"


def test_non_wav_is_rejected() -> None:
    with pytest.raises(AppError) as caught:
        pcm_from_wav(b"not-wav-data!!")
    assert caught.value.code == "unsupported_audio"
