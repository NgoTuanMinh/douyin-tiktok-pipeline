import json
import os
import shutil
import sys
from pathlib import Path
from utils import download_video_direct as download_douyin_video, crop_subtitle, transcribe_audio, translate_text

INPUT_JSON_DIR = Path("input")
STEP1_OUTPUT = Path("step1_output")
VIDEO_DIR = STEP1_OUTPUT / "videos"
SCRIPT_DIR = STEP1_OUTPUT / "scripts"
MAPPING_FILE = STEP1_OUTPUT / "mapping.json"

def ensure_dirs():
    STEP1_OUTPUT.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(exist_ok=True)
    SCRIPT_DIR.mkdir(exist_ok=True)

def process_one_video(task):
    vid = task.get("video_id", task.get("douyin_video_url", "").split("/")[-1].split("?")[0])
    url = task.get("download_video_url")
    if not url:
        raise Exception(f"Không tìm thấy download_video_url cho video {vid} trong json input.")
    has_audio = task.get("has_audio_speech", False)
    has_sub = task.get("has_hard_subtitle", False)
    product_name = task.get("product_name_viet", "")

    print(f"==> Xử lý video {vid}")

    temp_video = f"temp_{vid}.mp4"
    download_douyin_video(url, temp_video)

    final_video = VIDEO_DIR / f"{vid}.mp4"
    if has_sub:
        crop_subtitle(temp_video, str(final_video))
        os.remove(temp_video)
    else:
        shutil.move(temp_video, final_video)

    script_path = None
    if has_audio:
        transcript = transcribe_audio(str(final_video))
        viet_script = translate_text(transcript)
        script_path = SCRIPT_DIR / f"{vid}.txt"
        script_path.write_text(viet_script, encoding='utf-8')
        print(f"   Đã lưu script: {script_path}")

    # Không lưu viet_script vào mapping để tránh nặng
    return {
        "video_id": vid,
        "video_path": str(final_video),
        "script_path": str(script_path) if script_path else None,
        "product_name": product_name
    }

def main():
    # Ensure Vietnamese text prints correctly on Windows consoles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ensure_dirs()
    json_files = list(INPUT_JSON_DIR.glob("*.json"))
    if not json_files:
        print("Không tìm thấy file JSON nào trong thư mục input/")
        return
    input_file = json_files[0]
    with open(input_file, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    results = []
    for task in tasks:
        res = process_one_video(task)
        results.append(res)

    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n✅ Step 1 hoàn tất!")
    print(f"   Video đã crop: {VIDEO_DIR}")
    print(f"   Script tiếng Việt: {SCRIPT_DIR}")
    print(f"   Mapping file: {MAPPING_FILE}")
    print("\n👉 Tiếp theo, hãy dùng script trong thư mục scripts/ để tạo file MP3, đặt vào thư mục 'mp3_input/' với cùng tên (vid.mp3).")
    print("   Sau đó chạy step2.py")

if __name__ == "__main__":
    main()