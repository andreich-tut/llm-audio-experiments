"""
CLI tool: split a large audio file and send each chunk to the bot as a voice/audio message.

Usage:
    python send_chunks.py <audio_file> <chat_id> [--keep]

    audio_file  Path to any audio/video file (webm, mp3, ogg, mp4, …)
    chat_id     Telegram chat ID to send chunks to (your own ID works fine)
    --keep      Keep chunk files after sending (default: delete them)

Requires BOT_TOKEN in .env (same file the bot uses).
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audio_splitter import split_file

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_audio(chat_id: str, path: str) -> dict:
    with open(path, "rb") as f:
        resp = httpx.post(
            f"{TG_API}/sendAudio",
            data={"chat_id": chat_id},
            files={"audio": (Path(path).name, f, "audio/webm")},
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Split audio and send chunks to Telegram bot")
    parser.add_argument("audio_file", help="Input audio/video file")
    parser.add_argument("chat_id", help="Telegram chat ID to send to")
    parser.add_argument("--keep", action="store_true", help="Keep chunk files after sending")
    args = parser.parse_args()

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.audio_file):
        print(f"ERROR: File not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)

    # Split into chunks in a temp dir
    tmp_dir = tempfile.mkdtemp(prefix="tg_chunks_")
    prefix = os.path.join(tmp_dir, "chunk")

    print(f"Splitting {args.audio_file}...")
    chunks = split_file(args.audio_file, prefix=prefix)
    print(f"\nSending {len(chunks)} chunk(s) to chat {args.chat_id}...")

    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {Path(chunk).name} ... ", end="", flush=True)
        try:
            result = send_audio(args.chat_id, chunk)
            if result.get("ok"):
                print("sent")
            else:
                print(f"FAILED: {result.get('description')}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            print(f"ERROR: {e}")

        if not args.keep:
            os.remove(chunk)

        # Small delay to avoid hitting Telegram rate limits
        if i < len(chunks):
            time.sleep(0.5)

    if not args.keep:
        os.rmdir(tmp_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
