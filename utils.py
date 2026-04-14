import subprocess
import os
import json
from pathlib import Path
import yt_dlp
import whisper
import google.generativeai as genai
from telegram import Bot
from dotenv import load_dotenv

# ------------------- Cấu hình -------------------
load_dotenv()

GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DOUYIN_COOKIEFILE = os.getenv("DOUYIN_COOKIEFILE", "douyin_cookies.txt")
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")

_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    return _whisper_model

def _ensure_genai_configured():
    if not GENAI_API_KEY:
        raise RuntimeError("Thiếu GENAI_API_KEY (hãy set trong env hoặc file .env)")
    genai.configure(api_key=GENAI_API_KEY)

# ------------------- Tải video -------------------
def download_douyin_video(url, output_path):
    ydl_opts = {
        'cookiefile': DOUYIN_COOKIEFILE,
        'outtmpl': output_path,
        'quiet': False,
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    if not os.path.exists(output_path):
        base = Path(output_path).stem
        for f in Path('.').glob(f"{base}.*"):
            if f.suffix in ['.mp4', '.webm']:
                f.rename(output_path)
                break
    return output_path

# ------------------- Crop phụ đề -------------------
def crop_subtitle(input_video, output_video, crop_percent=0.15):
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=height', '-of', 'csv=p=0', input_video],
        capture_output=True, text=True
    )
    height = int(probe.stdout.strip())
    crop_height = int(height * (1 - crop_percent))
    cmd = ['ffmpeg', '-i', input_video, '-vf', f'crop=in_w:{crop_height}:0:0',
           '-c:a', 'copy', '-y', output_video]
    subprocess.run(cmd, check=True)
    return output_video

# ------------------- Transcribe -------------------
def transcribe_audio(video_path):
    result = _get_whisper_model().transcribe(video_path, language="zh")
    return result["text"]

# ------------------- Dịch -------------------
def translate_text(text, target_lang="vi"):
    _ensure_genai_configured()
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"Dịch đoạn văn sau từ tiếng Trung sang tiếng Việt, giữ nguyên phong cách quảng cáo, tự nhiên:\n\n{text}"
    response = model.generate_content(prompt)
    return response.text

# ------------------- Sinh caption -------------------
def generate_caption(product_name):
    _ensure_genai_configured()
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"Tạo caption ngắn gọn, thu hút cho sản phẩm '{product_name}' trên TikTok, kèm 3-5 hashtag phù hợp. Xuất theo format: CAPTION: ... | HASHTAGS: #a #b"
    response = model.generate_content(prompt)
    text = response.text
    caption_part = text.split("| HASHTAGS:")[0].replace("CAPTION:", "").strip()
    hashtag_part = text.split("| HASHTAGS:")[1].strip() if "| HASHTAGS:" in text else ""
    return caption_part, hashtag_part

# ------------------- Gửi Telegram (sửa lỗi tên file tạm) -------------------
def send_telegram_notification(video_path, metadata):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Thiếu TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID (hãy set trong env hoặc file .env)")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    with open(video_path, 'rb') as v:
        bot.send_video(TELEGRAM_CHAT_ID, v, caption=metadata.get('caption', ''))
    # Dùng tên file tạm theo video_id để tránh ghi đè
    vid = metadata.get('video_id', 'unknown')
    temp_meta = f"temp_metadata_{vid}.json"
    with open(temp_meta, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    with open(temp_meta, 'rb') as f:
        bot.send_document(TELEGRAM_CHAT_ID, f)
    os.remove(temp_meta)