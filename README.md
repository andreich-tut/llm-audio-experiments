# 🎙 Telegram Voice → LLM Bot

Локальный Telegram-бот: голосовые сообщения → faster-whisper (STT) → Ollama (LLM) → текстовый ответ.

## Требования

- Python 3.11+
- NVIDIA GPU с CUDA (для faster-whisper на GPU)
- Ollama запущена и доступна на `localhost:11434`
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))

## Быстрый старт

```bash
# 1. Клонируй / скопируй проект
cd telegram-voice-llm

# 2. Создай venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Настрой конфиг
cp .env.example .env
# Отредактируй .env — вставь BOT_TOKEN и свой user ID

# 5. Убедись что Ollama запущена и модель скачана
ollama pull qwen3:8b

# 6. Запусти бота
python bot.py
```

## Команды бота

| Команда    | Описание                                     |
|------------|----------------------------------------------|
| `/start`   | Приветствие и инструкция                     |
| `/mode`    | Переключить режим (чат / только расшифровка) |
| `/clear`   | Очистить историю диалога                     |
| `/model`   | Показать текущую модель                      |
| `/ping`    | Проверить доступность Ollama                 |
| `/savedoc` | Включить/выключить сохранение в Google Docs  |

## Использование

1. Отправь голосовое сообщение — бот распознает речь и ответит
2. Или просто напиши текстом — бот ответит через LLM
3. Бот помнит контекст диалога (последние 20 пар сообщений)

## Настройки Whisper

| Модель    | VRAM   | Скорость | Качество RU |
|-----------|--------|----------|-------------|
| `tiny`    | ~1 GB  | ⚡⚡⚡   | ★★☆☆☆       |
| `small`   | ~2 GB  | ⚡⚡     | ★★★☆☆       |
| `medium`  | ~5 GB  | ⚡       | ★★★★☆       |
| `large-v3`| ~10 GB | 🐢       | ★★★★★       |

С RTX 4070 Ti Super (16GB) можно спокойно использовать `medium`, и даже `large-v3` если Ollama не нагружает GPU одновременно.

## Google Docs (опционально)

Бот может сохранять расшифровки голосовых сообщений в Google Docs.

### Настройка

1. **Создай сервисный аккаунт** в [Google Cloud Console](https://console.cloud.google.com/):
   - IAM & Admin → Service Accounts → Create
   - Скачай JSON-ключ (Actions → Manage keys → Add key → JSON)

2. **Включи Google Docs API** в своём GCP-проекте:
   - APIs & Services → Enable APIs → поиск "Google Docs API" → Enable

3. **Открой нужный Google Doc** и поделись им с email сервисного аккаунта (`...@....iam.gserviceaccount.com`) с ролью **Editor**.

4. **Скопируй ID документа** из URL:
   ```
   https://docs.google.com/document/d/<DOCUMENT_ID>/edit
   ```

5. **Добавь в `.env`**:
   ```
   GDOCS_CREDENTIALS_FILE=/absolute/path/to/service-account-key.json
   GDOCS_DOCUMENT_ID=your_document_id_here
   ```

6. **Перезапусти бота** — в логах появится: `Google Docs integration enabled.`

### Использование

```
/savedoc   — включить сохранение расшифровок в документ
/savedoc   — повторно — выключить
```

Каждая расшифровка добавляется в конец документа в формате:
```
[2026-03-15 09:41 UTC] @username
Текст расшифровки голосового сообщения...

```

## Безопасность

- Обязательно задай `ALLOWED_USERS` в `.env` чтобы ограничить доступ
- Узнать свой Telegram ID: написать [@userinfobot](https://t.me/userinfobot)
- Бот хранит историю только в RAM, при перезапуске всё сбрасывается

## Архитектура

```
Telegram Voice → download .ogg → faster-whisper (GPU) → текст
                                                          ↓
Telegram ← текстовый ответ ← Ollama API ← текст с контекстом
```

---

## CLI-инструменты ([tools/](tools/))

Утилиты для работы с аудиофайлами локально, без запуска бота. Подробная документация: [tools/README.md](tools/README.md).

### transcribe_cli.py — Простая расшифровка

Транскрибирует файлы той же моделью Whisper что и бот. Ollama не нужна.

```bash
python tools/transcribe_cli.py recording.ogg
python tools/transcribe_cli.py lecture.webm -o result.txt
python tools/transcribe_cli.py part1.webm part2.webm part3.webm -o result.txt
```

### transcribe_diarize.py — Расшифровка с определением спикеров

Транскрибирует аудио и помечает кто что сказал, используя whisperX + pyannote.audio.

```bash
pip install whisperx  # установить один раз

python tools/transcribe_diarize.py meeting.mp3
python tools/transcribe_diarize.py meeting.mp3 --min-speakers 2 --max-speakers 3 -o transcript.txt
```

Вывод:
```
[00:00:01 - 00:00:05] SPEAKER_00: Привет, как дела?
[00:00:06 - 00:00:09] SPEAKER_01: Всё хорошо, спасибо.
```

Требует `HF_TOKEN` в `.env` (бесплатный токен HuggingFace). См. [tools/README.md](tools/README.md) для настройки.

### audio_splitter.py — Разбивка больших файлов

Разбивает аудио/видео файл на части с помощью ffmpeg.

```bash
python tools/audio_splitter.py lecture.webm --minutes 5
```

Результат: `lecture_000.webm`, `lecture_001.webm`, ... — рядом с исходным файлом.

### send_chunks.py — Отправка больших файлов боту

Telegram Bot API ограничивает загрузку файлов до 20 МБ. Этот инструмент разбивает файл и отправляет чанки боту напрямую.

```bash
python tools/send_chunks.py big_recording.webm 123456789
```

- `chat_id` — твой Telegram ID (узнать: [@userinfobot](https://t.me/userinfobot))
- Требует `BOT_TOKEN` в `.env` и `ffmpeg`/`ffprobe`
