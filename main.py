import os
import time
import requests
from io import BytesIO
from PIL import Image, ImageSequence
from datetime import datetime

from flask import Flask, send_file, send_from_directory
import threading

app = Flask(__name__)

# ========== НАСТРОЙКИ ==========
GIF_URL = "https://meteoinfo.ru/hmc-output/rmap/phenomena.gif"
CHECK_INTERVAL = 600

MINX = 18.67942748094448
MINY = 42.07763077261187
MAXX = 62.60899643948548
MAXY = 68.22855697214425

# ========== WORKER ==========
def download_gif():
    print(f"[{datetime.now()}] 📥 Download GIF")
    resp = requests.get(GIF_URL, timeout=30)
    resp.raise_for_status()
    gif = Image.open(BytesIO(resp.content))

    frames = [f.convert("RGBA") for f in ImageSequence.Iterator(gif)]
    print(f"[{datetime.now()}] 🎞 frames: {len(frames)}")
    return frames


def save_frame(frame, index):
    png_path = f"frame_{index}.png"
    frame.save(png_path, "PNG")

    width, height = frame.size
    pixel_width = (MAXX - MINX) / width
    pixel_height = (MAXY - MINY) / height

    pgw = f"{pixel_width}\n0\n0\n-{pixel_height}\n{MINX}\n{MAXY}"
    with open(f"frame_{index}.pgw", "w") as f:
        f.write(pgw)


def cleanup():
    for f in os.listdir("."):
        if f.startswith("frame_"):
            os.remove(f)


def refresh():
    print(f"[{datetime.now()}] 🔄 refresh start")
    cleanup()
    frames = download_gif()

    for i, f in enumerate(frames, 1):
        save_frame(f, i)

    print(f"[{datetime.now()}] ✅ done")


def worker():
    print("🚀 WORKER STARTED")
    refresh()

    while True:
        time.sleep(CHECK_INTERVAL)
        refresh()


# ========== WEB ==========
@app.route("/")
def home():
    return send_file("radanim.html")


@app.route("/<path:filename>")
def files(filename):
    return send_from_directory(".", filename)


@app.route("/api/frames")
def api():
    return {"frames": len([f for f in os.listdir(".") if f.endswith(".png")])}


# ========== START ==========
if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()

    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
