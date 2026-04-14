# Douyin → TikTok Video Processing Pipeline (2‑Step)

Hệ thống tự động tải video Douyin, cắt phụ đề, transcribe, dịch script, và ghép giọng đọc tiếng Việt. Dành cho Windows, chạy thủ công 5‑10 video/ngày.

## Yêu cầu hệ thống

- Windows 10/11
- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html) – tải bản `ffmpeg-release-full.7z`, giải nén và thêm đường dẫn `bin` vào biến môi trường PATH.
- Tài khoản Douyin (để lấy cookie) và Gemini API key.

## Cài đặt

1. **Clone hoặc tải mã nguồn** về máy.
2. **Mở Command Prompt (Admin)** trong thư mục dự án.
3. **Cài Python packages:**
   ```bash
   pip install -r requirements.txt
   ```
   Cài FFmpeg (nếu chưa):

Tải từ gyan.dev

Giải nén vào C:\ffmpeg

Thêm C:\ffmpeg\bin vào PATH (System Properties → Environment Variables)

Tạo file cookie Douyin:

Dùng trình duyệt Chrome, đăng nhập Douyin.

Cài extension Get cookies.txt

Xuất cookie của domain douyin.com thành file douyin_cookies.txt đặt cùng thư mục step1.py.

Cấu hình API keys:

Mở utils.py, thay YOUR_GEMINI_API_KEY, YOUR_BOT_TOKEN, YOUR_CHAT_ID (nếu dùng Telegram).

Chuẩn bị input
Tạo file JSON trong thư mục input/ (ví dụ batch_01.json):
[
{
"video_id": "001",
"douyin_video_url": "https://v.douyin.com/xxxxx/",
"product_name_viet": "Máy tách hạt ngô cầm tay",
"has_audio_speech": true,
"has_hard_subtitle": false
}
]
video_id: tuỳ chọn, nếu không có sẽ tự sinh từ URL.

has_audio_speech: true nếu video có giọng nói tiếng Trung.

has_hard_subtitle: true nếu có phụ đề cứng cần crop.
Cách chạy
Bước 1 – Xử lý tự động
bash
python step1.py
Kết quả:

step1_output/videos/ – video đã crop (giữ nguyên audio gốc)

step1_output/scripts/ – file .txt chứa script tiếng Việt (đã dịch)

step1_output/mapping.json – thông tin mapping

Bước thủ công (bạn làm)
Dùng nội dung các file .txt trong step1_output/scripts/ để tạo file MP3 (bằng Zalo TTS, Google TTS, hoặc thu âm).

Đặt các file MP3 vào thư mục mp3_input/ với tên trùng video_id (ví dụ 001.mp3 cho 001.mp4).

Bước 2 – Ghép audio và xuất video
bash
python step2.py
Kết quả:

step2*output/final*\*.mp4 – video hoàn chỉnh (đã thay audio)

step2*output/metadata*\*.json – caption, hashtag cho TikTok

Gửi thông báo Telegram (nếu đã cấu hình)

Ghi chú quan trọng
Cookie Douyin hết hạn sau vài ngày → cần xuất lại và thay file douyin_cookies.txt.

Nếu video không có has_audio_speech, step1 không tạo script, step2 bỏ qua.

Có thể chạy nhiều batch bằng cách đặt nhiều file JSON trong input/ (step1 xử lý file đầu tiên theo thứ tự alphabet).

Xử lý lỗi thường gặp
ffmpeg not found: cài lại FFmpeg và kiểm tra PATH.

HTTP Error 412: cookie hết hạn → xuất cookie mới.

No module named 'whisper': chạy pip install openai-whisper (lưu ý tên package).

Gemini lỗi quota: kiểm tra API key hoặc dùng tài khoản khác.

Giấy phép
Dành cho mục đích học tập và tham khảo. Vui lòng tuân thủ bản quyền nội dung khi up lên TikTok.

text

---

## 6. File `.gitignore`

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Secrets
douyin_cookies.txt
*_key.py
*.key
config.py

# Output thư mục
step1_output/
step2_output/
mp3_input/
input/*.json
!input/README.md

# Tạm thời
temp_*
*.tmp
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# Windows
Thumbs.db
desktop.ini
```
