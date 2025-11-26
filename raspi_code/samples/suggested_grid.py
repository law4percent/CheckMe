import cv2
import numpy as np
import math
import base64

# ------------------------
# Combine images into a smart grid
# ------------------------
def smart_grid_auto(image_paths, tile_width=400):
    """
    image_paths: list of image file paths
    tile_width: width of each tile in the grid
    Returns:
        combined_image: the final grid image (numpy array)
        base64_string: base64 encoded string of the image
    """
    # Load images
    imgs = [cv2.imread(p) for p in image_paths]
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)
    
    if n == 0:
        raise ValueError("No valid images provided.")

    # Determine grid size (ceil(sqrt(n)))
    grid_size = math.ceil(math.sqrt(n))
    rows = cols = grid_size

    # Compute tile height maintaining aspect ratio (assuming approx 1.4)
    tile_height = int(tile_width * 1.4)
    tile_size = (tile_width, tile_height)

    # Resize images
    resized_imgs = []
    for img in imgs:
        resized = cv2.resize(img, tile_size)
        resized_imgs.append(resized)

    # Fill empty slots with blank images
    while len(resized_imgs) < rows * cols:
        blank = np.zeros((tile_height, tile_width, 3), dtype=np.uint8) + 255  # white
        resized_imgs.append(blank)

    # Build the grid
    row_list = []
    for r in range(rows):
        row_imgs = resized_imgs[r*cols:(r+1)*cols]
        row_list.append(np.hstack(row_imgs))
    combined_image = np.vstack(row_list)

    # Convert to base64
    _, buffer = cv2.imencode('.jpg', combined_image)
    base64_string = base64.b64encode(buffer).decode('utf-8')

    return combined_image, base64_string


images = [
    "page1.jpg",
    "page2.jpg",
    "page3.jpg",
    "page4.jpg",
    "page5.jpg"
]

combined_img, combined_base64 = smart_grid_auto(images, tile_width=400)

# Save result
cv2.imwrite("combined_grid.jpg", combined_img)

# Print size info
print("Number of images:", len(images))
print("Base64 string length:", len(combined_base64))
