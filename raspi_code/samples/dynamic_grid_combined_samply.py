import cv2
import numpy as np
import base64
import os

MIN_WIDTH = 300          # minimum per-page width for good OCR
TARGET_SIZE_MB = 1.5     # final compressed image size
TARGET_BYTES = TARGET_SIZE_MB * 1024 * 1024

# ------------------------
# Resize function
# ------------------------
def resize_image(img, max_w=1200):
    h, w = img.shape[:2]
    if w > max_w:
        scale = max_w / w
        img = cv2.resize(img, (max_w, int(h * scale)))
    return img

# ------------------------
# Auto compression
# ------------------------
def compress_until_limit(img, limit_bytes=TARGET_BYTES):
    quality = 90
    while quality > 20:
        success, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if len(buffer) <= limit_bytes:
            return buffer.tobytes(), quality
        quality -= 5
    return buffer.tobytes(), quality

# ------------------------
# Try building a grid
# ------------------------
def build_grid(images, rows, cols, tile_size):
    resized_imgs = []
    for i in range(rows * cols):
        if i < len(images):
            img = cv2.resize(images[i], tile_size)
        else:
            img = np.zeros((tile_size[1], tile_size[0], 3), dtype=np.uint8)
        resized_imgs.append(img)

    row_list = []
    for r in range(rows):
        row_imgs = resized_imgs[r*cols:(r+1)*cols]
        row_list.append(np.hstack(row_imgs))

    return np.vstack(row_list)

# ------------------------
# MAIN: Smart Grid Builder
# ------------------------
def smart_grid(image_paths):
    imgs = [cv2.imread(path) for path in image_paths]
    imgs = [resize_image(img) for img in imgs if img is not None]

    count = len(imgs)
    grid_options = []

    # possible layouts
    for rows in range(1, 5):
        for cols in range(1, 5):
            if rows * cols >= count:
                grid_options.append((rows, cols))

    best_grid = None
    best_tile_w = 0

    for rows, cols in grid_options:
        # compute per-tile size
        grid_w = 1800
        tile_w = grid_w // cols
        tile_h = int(tile_w * 1.4)
        tile_size = (tile_w, tile_h)

        if tile_w < MIN_WIDTH:
            continue  # reject low resolution pages

        grid = build_grid(imgs, rows, cols, tile_size)

        if tile_w > best_tile_w:
            best_tile_w = tile_w
            best_grid = grid

    if best_grid is None:
        raise Exception("Cannot build a grid with acceptable OCR resolution.")

    # compress
    jpeg_data, used_quality = compress_until_limit(best_grid)

    base64_string = base64.b64encode(jpeg_data).decode('utf-8')

    return {
        "grid_image": best_grid,
        "base64": base64_string,
        "tile_width": best_tile_w,
        "jpeg_quality": used_quality,
        "final_size_kb": len(jpeg_data) // 1024
    }


result = smart_grid([
    "page1.jpg",
    "page2.jpg",
    "page3.jpg",
    "page4.jpg",
    "page5.jpg",
    "page6.jpg",
    "page7.jpg",
    "page8.jpg",
    "page9.jpg"
])

print("Tile width :", result["tile_width"])
print("JPEG quality:", result["jpeg_quality"])
print("Final size:", result["final_size_kb"], "KB")

final_image_base64 = result["base64"]
