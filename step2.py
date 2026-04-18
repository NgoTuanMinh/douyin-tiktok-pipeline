import json
import shutil
from pathlib import Path
import subprocess
from utils import generate_caption, send_telegram_notification, ensure_dirs, close_gemini_client

STEP1_VIDEO_DIR = Path("step1_output/videos")
MP3_DIR = Path("mp3_input")
STEP2_OUTPUT = Path("step2_output")
MAPPING_FILE = Path("step1_output/mapping.json")

def replace_audio_in_video(video_path, audio_path, output_path):
    cmd = ['ffmpeg', '-i', str(video_path), '-i', str(audio_path),
           '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0',
           '-shortest', '-y', str(output_path)]
    subprocess.run(cmd, check=True)

def main():
    ensure_dirs([STEP2_OUTPUT, MP3_DIR])
    
    if not MAPPING_FILE.exists():
        print("Chưa chạy step1 hoặc không tìm thấy mapping.json")
        return

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    try:
        for item in mapping:
            vid = item["video_id"]
            video_file = STEP1_VIDEO_DIR / f"{vid}.mp4"
            mp3_file = MP3_DIR / f"{vid}.mp3"
            output_video = STEP2_OUTPUT / f"final_{vid}.mp4"

            if not video_file.exists():
                print(f"⚠️ Không tìm thấy video {vid} trong {STEP1_VIDEO_DIR}")
                continue

            # Ghép audio nếu có MP3, không thì copy video gốc
            if mp3_file.exists():
                print(f"==> Ghép audio cho {vid}")
                replace_audio_in_video(video_file, mp3_file, output_video)
            else:
                print(f"==> Không có MP3 cho {vid}, copy video gốc")
                shutil.copy2(video_file, output_video)

            # Tạo metadata cho TẤT CẢ video (kể cả không có MP3)
            product_name = item.get("product_name", "")
            print(f"  - Sinh caption cho {product_name}...")
            caption, hashtags = generate_caption(product_name)
            full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption

            has_audio = mp3_file.exists()
            metadata = {
                "video_id": vid,
                "product_name": product_name,
                "caption": full_caption,
                "video_path": str(output_video),
                "has_custom_audio": has_audio
            }
            metadata_file = STEP2_OUTPUT / f"metadata_{vid}.json"
            with open(metadata_file, 'w', encoding='utf-8') as mf:
                json.dump(metadata, mf, indent=2, ensure_ascii=False)
            print(f"  - Đã lưu metadata_{vid}.json")

            try:
                send_telegram_notification(str(output_video), metadata)
                print(f"  - Đã gửi {vid} lên Telegram")
            except Exception as e:
                print(f"  - Lỗi gửi Telegram: {e}")
    finally:
        close_gemini_client()

    print("\n✅ Step 2 hoàn tất! Video cuối cùng nằm trong thư mục step2_output/")

if __name__ == "__main__":
    main()