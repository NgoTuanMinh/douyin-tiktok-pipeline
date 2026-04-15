import subprocess
import os
import json
from pathlib import Path
import yt_dlp
import whisper
import google.generativeai as genai
from telegram import Bot
from dotenv import load_dotenv
import requests
import time
import re
from playwright.sync_api import sync_playwright

# ===== CẤU HÌNH API =====
# Đường dẫn đến thư mục bạn vừa clone API ở Bước 1
API_PROJECT_PATH = r"E:\ToolAir\Douyin_TikTok_Download_API" 
# Địa chỉ API sẽ chạy trên máy local
API_BASE_URL = "http://127.0.0.1:8000"

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

def start_api_server():
    """Khởi động server API trong một tiến trình riêng biệt."""
    import subprocess
    import sys
    import os
    # Kiểm tra nếu server chưa chạy, hãy khởi động nó
    try:
        requests.get(f"{API_BASE_URL}/docs", timeout=2)
        print("API server đã hoạt động.")
    except requests.ConnectionError:
        print("Đang khởi động API server...")
        # Chạy server bằng lệnh uvicorn
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=API_PROJECT_PATH,
            shell=True
        )
        time.sleep(5) # Chờ server khởi động
        print("API server đã sẵn sàng.")

# Chạy lệnh này trước khi chạy step 1: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# ------------------- Tải video -------------------
def download_douyin_video(url, output_path):
    """Tải video Douyin bằng Douyin_TikTok_Download_API."""
    # Đảm bảo server API đã chạy
    # start_api_server()
    
    # Gọi API để lấy thông tin video
    api_endpoint = f"{API_BASE_URL}/api/download"
    params = {"url": url, "prefix": "true", "with_watermark": "false"}
    
    print(f"Đang gửi yêu cầu tới API: {api_endpoint}")
    response = requests.get(api_endpoint, params=params)
    
    if response.status_code != 200:
        raise Exception(f"API trả về lỗi: {response.status_code} - {response.text}")
    
    # Parse kết quả từ API
    result = response.json()
    
    if result.get("status") != "success" or not result.get("video_data"):
        raise Exception(f"API không tìm thấy video. Phản hồi: {result}")
    
    # Lấy link video không watermark
    video_url = result["video_data"]["video_url"]
    if not video_url:
        raise Exception("API không trả về link video.")
    
    # Tải video về từ link trực tiếp
    print(f"Đang tải video từ: {video_url}")
    video_response = requests.get(video_url, stream=True)
    if video_response.status_code != 200:
        raise Exception(f"Lỗi tải video: {video_response.status_code}")
    
    # Ghi file ra đĩa
    with open(output_path, 'wb') as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Đã lưu video thành công tại: {output_path}")
    return output_path

def download_douyin_video_playwright(url, output_path, max_retries=3):
    """
    Dùng playwright mở douyin.wtf, paste link, click download, lấy link file .mp4.
    """
    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)  # False để debug
                page = browser.new_page()
                page.goto("https://tikgo.me/douyin/", timeout=30000)
                
                # Chờ input xuất hiện (selector có thể thay đổi, cần cập nhật)
                # Hiện tại douyin.wtf dùng input có class "form-control" hoặc name "url"
                input_selector = "input[id='download-url-input']"  # hoặc "input[name='url']"
                page.wait_for_selector(input_selector, timeout=10000)
                page.fill(input_selector, url)
                
                # Click nút download (thường có text "Download" hoặc "Get Video")
                download_btn = page.locator("button:has-text('Download')")
                if download_btn.count() == 0:
                    download_btn = page.locator("button:has-text('Get')")

                if download_btn.count() == 0:
                    download_btn = page.locator("button[class*='TikTokDownloader_downloadButton']")

                download_btn.click()
                
                # Chờ link tải xuất hiện (thường trong thẻ <a> chứa .mp4)
                time.sleep(10)  # chờ xử lý
                video_link_elem = page.locator("a[href*='.mp4']").first
                if not video_link_elem:
                    # fallback: tìm trong script
                    html = page.content()
                    match = re.search(r'''https?://[^\s"']+\.mp4''', html)
                    if match:
                        video_url = match.group(0)
                    else:
                        raise Exception("Không tìm thấy link MP4")
                else:
                    video_url = video_link_elem.get_attribute("href")
                
                browser.close()
                
                # Tải file MP4 bằng requests
                r = requests.get(video_url, stream=True, timeout=60)
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return output_path
                
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