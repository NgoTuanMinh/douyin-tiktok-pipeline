# Douyin → TikTok pipeline (2 bước)

Pipeline này giúp bạn:

- Tải video Douyin
- (Tuỳ chọn) crop phụ đề cứng
- (Tuỳ chọn) nhận dạng giọng nói (Whisper) và dịch sang tiếng Việt (Gemini)
- Ghép file MP3 tiếng Việt vào video và tạo caption/hashtag (Gemini)
- (Tuỳ chọn) gửi video + metadata lên Telegram

## Yêu cầu

- Python **3.9+**
- **FFmpeg** (có `ffmpeg` và `ffprobe` trong PATH)
- (Tuỳ chọn) **cookie Douyin** nếu gặp lỗi tải/HTTP 412
- API key **Gemini** nếu dùng dịch/caption
- Token **Telegram** nếu muốn gửi thông báo

## Cài đặt

```bash
pip install -r requirements.txt
```

## Cấu hình (ENV)

1. Copy `.env.example` thành `.env`

2. Điền các biến môi trường cần thiết trong `.env`:

- `GENAI_API_KEY` (bắt buộc nếu dùng dịch/caption)
- `GEMINI_MODEL` (mặc định `gemini-pro`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (chỉ cần nếu gửi Telegram)
- `DOUYIN_COOKIEFILE` (mặc định `douyin_cookies.txt`)
- `WHISPER_MODEL` (mặc định `base`)

## Chuẩn bị input

Tạo **một** file JSON trong `input/` (ví dụ `input/batch_01.json`) có dạng mảng:

```json
[
  {
    "video_id": "001",
    "douyin_video_url": "https://v.douyin.com/xxxxx/",
    "product_name_viet": "Máy tách hạt ngô cầm tay",
    "has_audio_speech": true,
    "has_hard_subtitle": false
  }
]
```

- `video_id`: tuỳ chọn (nếu không có sẽ tự sinh từ URL)
- `has_audio_speech`: `true` nếu video có lời thoại tiếng Trung để transcribe + dịch
- `has_hard_subtitle`: `true` nếu video có phụ đề cứng ở dưới cần crop

## Chạy pipeline

### Step 1 — tải/crop/transcribe/dịch

```bash
python step1.py
```

Output:

- `step1_output/videos/`: video đã xử lý (crop nếu cần)
- `step1_output/scripts/`: script tiếng Việt (nếu `has_audio_speech=true`)
- `step1_output/mapping.json`: mapping `video_id` ↔ đường dẫn output

### Bước thủ công — tạo MP3 tiếng Việt

Dùng nội dung trong `step1_output/scripts/*.txt` để tạo MP3 (Zalo TTS/Google TTS/thu âm…),
sau đó đặt vào `mp3_input/` với tên **trùng `video_id`** (ví dụ `001.mp3`).

### Step 2 — ghép MP3 + tạo caption + (tuỳ chọn) gửi Telegram

```bash
python step2.py
```

Output:

- `step2_output/final_<video_id>.mp4`: video cuối cùng đã thay audio
- `step2_output/metadata_<video_id>.json`: metadata gồm caption/hashtag

## Lưu ý

- Cookie Douyin có thể hết hạn sau vài ngày → export lại và thay file cookie.
- Nếu `has_audio_speech=false` thì Step 1 sẽ không tạo script; Step 2 vẫn ghép MP3 nếu bạn tự chuẩn bị.
- Nếu bật Telegram mà thiếu `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` thì Step 2 sẽ báo lỗi khi gửi.

## Troubleshooting nhanh

- **`ffmpeg not found` / `ffprobe not found`**: cài FFmpeg và đảm bảo PATH đúng.
- **HTTP Error 412 / tải Douyin fail**: cookie hết hạn hoặc thiếu → export cookie mới.
- **Thiếu package Python**: chạy lại `pip install -r requirements.txt`.

## Giấy phép

Dành cho mục đích học tập/tham khảo. Vui lòng tuân thủ bản quyền nội dung khi đăng tải.
