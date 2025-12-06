import numpy as np
import math
import cv2

def _smart_grid_auto(collected_images: list, tile_width: int) -> dict:
    """Arrange multiple images into a grid layout."""
    imgs = [cv2.imread(p) for p in collected_images]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)

    if n == 0:
        return {
            "status"    : "error", 
            "message"   : f"No valid images provided. Source: {__name__}."
        }

    try:
        # Compute grid dimensions
        grid_size = math.ceil(math.sqrt(n))
        rows = grid_size
        cols = grid_size

        # Compute tile size
        ASPECT_RATIO = 1.4
        tile_height = int(tile_width * ASPECT_RATIO)
        tile_size = (tile_width, tile_height)

        # Resize images to uniform size
        resized_imgs = []
        for img in imgs:
            resized_imgs.append(cv2.resize(img, tile_size))

        # Fill empty slots with white images
        total_slots = rows * cols
        while len(resized_imgs) < total_slots:
            blank = np.full((tile_height, tile_width, 3), 255, dtype=np.uint8)
            resized_imgs.append(blank)

        # Build grid row by row
        row_list = []
        for r in range(rows):
            start = r * cols
            end = start + cols
            row_imgs = resized_imgs[start:end]
            row_list.append(np.hstack(row_imgs))

        # Combine rows vertically
        combined_image = np.vstack(row_list)
        return {
            "status": "success", 
            "frame" : combined_image
        }

    except Exception as e:
        return {
            "status": "error", 
            "message": f"{e}. Source: {__name__}."
        }


def combine_images_into_grid(collected_images: list, tile_width: int) -> dict:
    """Combine multiple page images into a single grid image."""
    return _smart_grid_auto(collected_images, tile_width)