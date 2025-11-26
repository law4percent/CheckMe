import cv2
import numpy as np
import math
import base64
import os

def create_image_grid(image_paths, grid_size=(2, 2), resize_dim=(200, 200)):
    """
    Combine multiple images into a grid.
    
    :param image_paths: List of image file paths
    :param grid_size: Tuple (rows, cols)
    :param resize_dim: Tuple (width, height) to resize each image
    :return: Combined image (numpy array)
    """
    rows, cols = grid_size
    grid_images = []

    # Load and resize images
    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            continue
        img = cv2.resize(img, resize_dim)
        grid_images.append(img)

    # Fill empty slots with black images if not enough images
    while len(grid_images) < rows * cols:
        grid_images.append(np.zeros((resize_dim[1], resize_dim[0], 3), dtype=np.uint8))

    # Stack images row by row
    rows_list = []
    for r in range(rows):
        row_imgs = grid_images[r*cols:(r+1)*cols]
        row_stack = np.hstack(row_imgs)
        rows_list.append(row_stack)

    # Stack all rows vertically
    grid = np.vstack(rows_list)
    return grid

# Example usage
image_files = ["image1.jpeg", "image2.jpeg", "image3.jpeg", "image4.jpeg"]
grid_image = create_image_grid(image_files, grid_size=(2, 2), resize_dim=(200, 200))

# Save grid (optional)
cv2.imwrite("grid_combined.jpeg", grid_image)

# Convert to base64 for Gemini API
_, buffer = cv2.imencode('.jpeg', grid_image)
img_base64 = base64.b64encode(buffer).decode('utf-8')
