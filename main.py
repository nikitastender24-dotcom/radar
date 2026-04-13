import os
import time
import requests
import shutil
from io import BytesIO
from PIL import Image, ImageSequence
from datetime import datetime

from flask import Flask
import threading

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
GIF_URL = "https://meteoinfo.ru/hmc-output/rmap/phenomena.gif"
CLEANUP_HOURS = 2
CHECK_INTERVAL = 600

MINX = 18.67942748094448
MINY = 42.07763077261187
MAXX = 62.60899643948548
MAXY = 68.22855697214425

# ========== ТВОЙ КОД (НЕ ТРОГАЛ) ==========

def download_gif():
    print(f"[{datetime.now()}] 📥 Скачиваю гифку...")
    resp = requests.get(GIF_URL, timeout=30)
    resp.raise_for_status()
    gif = Image.open(BytesIO(resp.content))
    frames = []
    for frame in ImageSequence.Iterator(gif):
        frames.append(frame.convert("RGBA"))
    print(f"[{datetime.now()}] 🎞️ Загружено кадров: {len(frames)}")
    return frames

def save_frame(frame, index):
    png_path = f"frame_{index}.png"
    frame.save(png_path, "PNG")

    width, height = frame.size
    pixel_width = (MAXX - MINX) / width
    pixel_height = (MAXY - MINY) / height

    world_content = f"{pixel_width}\n0\n0\n-{pixel_height}\n{MINX}\n{MAXY}"
    pgw_path = f"frame_{index}.pgw"
    with open(pgw_path, 'w') as f:
        f.write(world_content)

    return png_path, pgw_path

def cleanup_old_frames():
    deleted = 0
    for f in os.listdir('.'):
        if f.startswith('frame_') and (f.endswith('.png') or f.endswith('.pgw')):
            os.remove(f)
            deleted += 1
    if deleted:
        print(f"[{datetime.now()}] 🗑️ Удалено {deleted} файлов")

def refresh_frames():
    print(f"[{datetime.now()}] 🔄 Обновление...")
    cleanup_old_frames()
    try:
        frames = download_gif()
        for i, frame in enumerate(frames, start=1):
            save_frame(frame, i)
        print(f"[{datetime.now()}] ✅ Готово")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Ошибка: {e}")

def worker():
    print("🚀 ДЕМОН ЗАПУЩЕН")
    refresh_frames()
    while True:
        time.sleep(CHECK_INTERVAL)
        refresh_frames()

# ========== FLASK СЕРВЕР (ВАЖНО) ==========

@app.route("/")
def home():
    files = os.listdir(".")
    images = [f for f in files if f.endswith(".png")]
    return {
        "status": "running",
        "frames": len(images)
    }

# ========== ЗАПУСК ==========

def start_worker():
    worker()

if __name__ == "__main__":
    threading.Thread(target=start_worker, daemon=True).start()

    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
