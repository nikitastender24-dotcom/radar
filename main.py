import os
import time
import requests
import shutil
from io import BytesIO
from PIL import Image, ImageSequence
from datetime import datetime

# ========== НАСТРОЙКИ ==========
GIF_URL = "https://meteoinfo.ru/hmc-output/rmap/phenomena.gif"
CLEANUP_HOURS = 2                   # удалять старые кадры старше 2 часов
CHECK_INTERVAL = 600                # 10 минут в секундах

# Координаты для world-файла (примерные — можно заменить на свои после подгонки)
# Формат: minx, miny, maxx, maxy в EPSG:4326 (градусы)
MINX = 18.67942748094448
MINY = 42.07763077261187
MAXX = 62.60899643948548
MAXY = 68.22855697214425

# ========== ФУНКЦИИ ==========

def download_gif():
    """Скачивает гифку и возвращает список кадров (PIL Images)"""
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
    """Сохраняет кадр как PNG + world-файл (.pgw) в текущую директорию"""
    # Сохраняем PNG
    png_path = f"frame_{index}.png"
    frame.save(png_path, "PNG")
    
    # Вычисляем размер пикселя в градусах
    width, height = frame.size
    pixel_width = (MAXX - MINX) / width
    pixel_height = (MAXY - MINY) / height
    
    # Содержимое world-файла (.pgw)
    world_content = f"{pixel_width}\n0\n0\n-{pixel_height}\n{MINX}\n{MAXY}"
    pgw_path = f"frame_{index}.pgw"
    with open(pgw_path, 'w') as f:
        f.write(world_content)
    
    return png_path, pgw_path

def cleanup_old_frames():
    """Удаляет все старые frame_*.png и frame_*.pgw в текущей директории"""
    deleted = 0
    for f in os.listdir('.'):
        if f.startswith('frame_') and (f.endswith('.png') or f.endswith('.pgw')):
            os.remove(f)
            deleted += 1
    if deleted:
        print(f"[{datetime.now()}] 🗑️ Удалено {deleted} старых файлов (frame_*.png / frame_*.pgw)")

def refresh_frames():
    """Основная функция: чистит старые кадры, скачивает гифку, сохраняет новые кадры"""
    print(f"[{datetime.now()}] 🔄 Начинаю обновление кадров...")
    cleanup_old_frames()
    try:
        frames = download_gif()
        total = len(frames)
        for i, frame in enumerate(frames, start=1):
            save_frame(frame, i)
            if i % 5 == 0:
                print(f"   Сохранено {i}/{total}")
        print(f"[{datetime.now()}] ✅ Сохранено {total} кадров в текущую директорию")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Ошибка при обновлении: {e}")

def worker():
    """Фоновый цикл демона"""
    print("=" * 50)
    print("🚀 ДЕМОН ЗАПУЩЕН")
    print(f"   Рабочая директория: {os.getcwd()}")
    print(f"   Проверка каждые {CHECK_INTERVAL // 60} минут")
    print(f"   Удаление старых кадров перед каждой новой загрузкой")
    print("=" * 50)
    
    # Первый запуск
    refresh_frames()
    
    # Бесконечный цикл
    while True:
        time.sleep(CHECK_INTERVAL)
        refresh_frames()

if __name__ == "__main__":
    try:
        worker()
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] ⏹️ Демон остановлен пользователем")
