import json
from pathlib import Path
import subprocess
import sys
from utils import generate_caption, send_telegram_notification

STEP1_VIDEO_DIR = Path("step1_output/videos")
MP3_DIR = Path("mp3_input")
STEP2_OUTPUT = Path("step2_output")
MAPPING_FILE = Path("step1_output/mapping.json")

def ensure_dirs():
    STEP2_OUTPUT.mkdir(parents=True, exist_ok=True)
    MP3_DIR.mkdir(exist_ok=True)

def replace_audio_in_video(video_path, audio_path, output_path):
    cmd = ['ffmpeg', '-i', str(video_path), '-i', str(audio_path),
           '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0',
           '-shortest', '-y', str(output_path)]
    subprocess.run(cmd, check=True)

def main():
    # Ensure Vietnamese text prints correctly on Windows consoles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ensure_dirs()
    if not MAPPING_FILE.exists():
        print("Chưa chạy step1 hoặc không tìm thấy mapping.json")
        return

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    for item in mapping:
        vid = item["video_id"]
        video_file = STEP1_VIDEO_DIR / f"{vid}.mp4"
        mp3_file = MP3_DIR / f"{vid}.mp3"
        output_video = STEP2_OUTPUT / f"final_{vid}.mp4"

        if not video_file.exists():
            print(f"⚠️ Không tìm thấy video {vid} trong {STEP1_VIDEO_DIR}")
            continue
        if not mp3_file.exists():
            print(f"⚠️ Không tìm thấy MP3 cho {vid} trong {MP3_DIR}, bỏ qua video này")
            continue

        print(f"==> Ghép audio cho {vid}")
        replace_audio_in_video(video_file, mp3_file, output_video)

        product_name = item.get("product_name", "")
        caption, hashtags = generate_caption(product_name)
        full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption

        metadata = {
            "video_id": vid,
            "product_name": product_name,
            "caption": full_caption,
            "video_path": str(output_video)
        }
        metadata_file = STEP2_OUTPUT / f"metadata_{vid}.json"
        with open(metadata_file, 'w', encoding='utf-8') as mf:
            json.dump(metadata, mf, indent=2, ensure_ascii=False)

        try:
            send_telegram_notification(str(output_video), metadata)
            print(f"   Đã gửi {vid} lên Telegram")
        except Exception as e:
            print(f"   Lỗi gửi Telegram: {e}")

    print("\n✅ Step 2 hoàn tất! Video cuối cùng nằm trong thư mục step2_output/")

if __name__ == "__main__":
    main()