import subprocess
import os
import json
from pathlib import Path
import yt_dlp
import whisper
from telegram import Bot
from dotenv import load_dotenv
import requests
import time
import re

# Import Gemini client từ file riêng
from gemini_client import GeminiWebClient

# ------------------- Cấu hình -------------------
load_dotenv()

GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DOUYIN_COOKIEFILE = os.getenv("DOUYIN_COOKIEFILE", "douyin_cookies.txt")
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")

_whisper_model = None
_gemini_client = None  # Global Gemini client instance

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    return _whisper_model


def get_gemini_client(headless: bool = True):
    """
    Lấy hoặc khởi tạo GeminiWebClient (singleton pattern)
    """
    global _gemini_client
    if _gemini_client is None:
        print("🚀 Khởi tạo Gemini Web Client lần đầu...")
        _gemini_client = GeminiWebClient(headless=headless)
        _gemini_client.start()
    return _gemini_client


def close_gemini_client():
    """
    Đóng Gemini client khi không cần dùng nữa
    """
    global _gemini_client
    if _gemini_client is not None:
        _gemini_client.close()
        _gemini_client = None

def download_video_direct(url, output_path, max_retries=3):
    """
    Tải video trực tiếp từ url cho trước không cần mở trình duyệt.
    """
    for attempt in range(max_retries):
        try:
            print(f"  Đang trực tiếp tải video từ link...")
            r = requests.get(url, stream=True, timeout=120)
            if r.status_code != 200:
                raise Exception(f"Lỗi tải video HTTP: {r.status_code}")
                
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"  Đã tải thành công: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"Lần thử {attempt+1} thất bại: {e}")
            time.sleep(5)
            continue
    raise Exception(f"Không thể tải video sau {max_retries} lần thử")

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


# ------------------- Dịch (dùng Gemini Web thay vì API) -------------------
def translate_text(text, target_lang="vi", max_retries=3):
    """
    Dịch văn bản sử dụng Gemini Web Client (vượt qua giới hạn API)
    """
    for attempt in range(max_retries):
        try:
            client = get_gemini_client()
            return client.translate(text)
        except Exception as e:
            print(f"  [Cảnh báo] Lần thử {attempt+1} dịch thất bại: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                # Refresh client nếu cần
                close_gemini_client()
            else:
                raise Exception(f"Không thể dịch text sau {max_retries} lần thử: {e}")


# ------------------- Sinh caption (dùng Gemini Web thay vì API) -------------------
def generate_caption(product_name, max_retries=3):
    """
    Sinh caption sử dụng Gemini Web Client (vượt qua giới hạn API)
    """
    for attempt in range(max_retries):
        try:
            client = get_gemini_client()
            return client.generate_caption(product_name)
        except Exception as e:
            print(f"  [Cảnh báo] Lần thử {attempt+1} sinh caption thất bại: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                close_gemini_client()
            else:
                raise Exception(f"Không thể sinh caption sau {max_retries} lần thử: {e}")


# ------------------- Gửi Telegram -------------------
def send_telegram_notification(video_path, metadata):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Thiếu TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID, bỏ qua gửi Telegram")
        return
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    with open(video_path, 'rb') as v:
        bot.send_video(TELEGRAM_CHAT_ID, v, caption=metadata.get('caption', '')[:1024])
    
    vid = metadata.get('video_id', 'unknown')
    temp_meta = f"temp_metadata_{vid}.json"
    with open(temp_meta, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    with open(temp_meta, 'rb') as f:
        bot.send_document(TELEGRAM_CHAT_ID, f)
    os.remove(temp_meta)


# ------------------- Hàm tiện ích -------------------
def ensure_dirs(dirs: list):
    """Đảm bảo các thư mục tồn tại"""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def clean_filename(name: str) -> str:
    """Làm sạch tên file, loại bỏ ký tự đặc biệt"""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def check_ffmpeg() -> bool:
    """Kiểm tra FFmpeg đã được cài đặt chưa"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg chưa được cài đặt hoặc không có trong PATH")
        print("   Vui lòng tải FFmpeg từ https://ffmpeg.org/download.html")
        print("   và thêm đường dẫn bin vào biến môi trường PATH")
        return False


# ------------------- Cleanup khi kết thúc -------------------
import atexit
atexit.register(close_gemini_client)


# Export các hàm cần dùng
__all__ = [
    'download_douyin_video',
    'download_video_direct',
    'crop_subtitle',
    'transcribe_audio',
    'translate_text',
    'generate_caption',
    'send_telegram_notification',
    'ensure_dirs',
    'clean_filename',
    'check_ffmpeg',
    'get_gemini_client',
    'close_gemini_client'
]