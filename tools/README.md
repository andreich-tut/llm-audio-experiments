# Tools

Standalone CLI utilities for working with audio files locally, without running the bot.

All tools read `WHISPER_MODEL`, `WHISPER_DEVICE`, and other settings from the root `.env` file.
Run them from the project root or from inside `tools/` — both work.

---

## transcribe_cli.py — Simple transcription

Transcribes audio/video files using the same faster-whisper model as the bot. No Ollama needed.

```bash
python tools/transcribe_cli.py recording.ogg
python tools/transcribe_cli.py lecture.webm -o result.txt
python tools/transcribe_cli.py part1.webm part2.webm part3.webm -o result.txt
```

- Output goes to stdout; logs are saved to `./logs/transcribe_<timestamp>.log`
- `-o/--output` saves transcript to a file (multiple files get `# filename` headers)
- Large files are split and transcribed in chunks automatically

---

## transcribe_diarize.py — Transcription + speaker diarization

Transcribes audio and labels who said what, using whisperX + pyannote.audio.

```bash
python tools/transcribe_diarize.py meeting.mp3
python tools/transcribe_diarize.py meeting.mp3 --min-speakers 2 --max-speakers 3
python tools/transcribe_diarize.py meeting.mp3 -o transcript.txt
python tools/transcribe_diarize.py audio.ogg --no-diarize    # transcribe only, with timestamps
python tools/transcribe_diarize.py audio.ogg --language ru   # force language
```

**Output format:**
```
[00:00:01 - 00:00:05] SPEAKER_00: Привет, как дела?
[00:00:06 - 00:00:09] SPEAKER_01: Всё хорошо, спасибо.
```

**One-time setup:**
1. Install whisperX: `pip install whisperx`
2. Create a free account at [huggingface.co](https://huggingface.co)
3. Accept license: [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
4. Accept license: [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
5. Generate token: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
6. Add to `.env`: `HF_TOKEN=your_token_here`

Models are downloaded once and run fully locally after that — no ongoing API calls or cost.

| Flag | Description |
|------|-------------|
| `--no-diarize` | Skip speaker detection, just transcribe with timestamps |
| `--min-speakers N` | Hint: minimum number of speakers (improves accuracy) |
| `--max-speakers N` | Hint: maximum number of speakers |
| `--language CODE` | Force language (e.g. `ru`, `en`). Auto-detected if omitted |
| `--hf-token TOKEN` | Pass HF token directly instead of via `.env` |
| `-o/--output FILE` | Save transcript to file |

---

## audio_splitter.py — Split large audio files

Splits audio/video files into chunks using ffmpeg. Useful before sending to the bot (Telegram limits uploads to 20 MB) or to reduce Whisper memory usage.

```bash
# Split by size (~18 MB per chunk, default)
python tools/audio_splitter.py lecture.webm

# Split by time (recommended for Whisper — more predictable memory)
python tools/audio_splitter.py lecture.webm --minutes 5

# Custom output prefix
python tools/audio_splitter.py lecture.webm --minutes 10 --prefix /tmp/parts/chunk
```

Output: `lecture_000.webm`, `lecture_001.webm`, ... — saved next to the source file by default.

Requires `ffmpeg` and `ffprobe`.

---

## send_chunks.py — Send large files to the bot via Telegram

Splits a file and sends each chunk to the bot as an audio message. Useful for files too large to send through the Telegram UI.

```bash
python tools/send_chunks.py big_recording.webm 123456789
python tools/send_chunks.py lecture.webm 123456789 --keep   # keep chunk files after sending
```

- `chat_id` — your Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot))
- Requires `BOT_TOKEN` in `.env` and `ffmpeg`/`ffprobe`

---

## split.sh — Legacy bash splitter

Simple bash script that splits a single hardcoded file. Superseded by `audio_splitter.py`.
