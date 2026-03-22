"""
Speech-to-text: faster-whisper transcription with audio chunking.
"""

import asyncio
import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from faster_whisper import WhisperModel

from config import WHISPER_MODEL, WHISPER_DEVICE

# Make tools/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from audio_splitter import split_file

logger = logging.getLogger(__name__)

logger.info("Loading Whisper model '%s' on %s...", WHISPER_MODEL, WHISPER_DEVICE)
_whisper = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")
logger.info("Whisper ready.")


def _transcribe_file(file_path: str) -> tuple[str, str]:
    logger.info("Calling whisper.transcribe()...")
    segments, info = _whisper.transcribe(
        file_path, language="ru", beam_size=5, vad_filter=True,
    )
    logger.info("Got segments generator, language=%s, duration=%.1fs", info.language, info.duration)
    parts = []
    for i, seg in enumerate(segments):
        logger.info("Segment %d [%.1f-%.1fs]: %s", i, seg.start, seg.end, seg.text[:60])
        parts.append(seg.text.strip())
    logger.info("Transcription done, %d segments", len(parts))
    return " ".join(parts), info.language


async def transcribe(file_path: str) -> str:
    """Run faster-whisper in a thread. Splits audio into 5-min chunks."""
    loop = asyncio.get_event_loop()
    t0 = time.time()
    tmp_dir = tempfile.mkdtemp()
    prefix = os.path.join(tmp_dir, "chunk")
    chunks = await loop.run_in_executor(None, lambda: split_file(file_path, prefix=prefix, max_minutes=5))
    logger.info("STT: split into %d chunks from %s", len(chunks), file_path)
    try:
        texts = []
        lang = "ru"
        for chunk in chunks:
            text, lang = await loop.run_in_executor(None, _transcribe_file, chunk)
            texts.append(text)
        full_text = " ".join(t for t in texts if t)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    elapsed = time.time() - t0
    logger.info("STT done: lang=%s, %.1fs, text_len=%d, preview=%s", lang, elapsed, len(full_text), full_text[:80])
    return full_text
