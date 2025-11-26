import numpy as np
import cv2

# Load images
img1 = cv2.imread("cat.jpg")
img2 = cv2.imread("dog.jpeg")

# Resize images to the same height (optional)
height = max(img1.shape[0], img2.shape[0])
img1 = cv2.resize(img1, (int(img1.shape[1] * height / img1.shape[0]), height))
img2 = cv2.resize(img2, (int(img2.shape[1] * height / img2.shape[0]), height))

# Combine images horizontally
combined = np.hstack((img1, img2))  # Use np.vstack for vertical stacking

# Save combined image (optional)
cv2.imwrite("combined.jpeg", combined)