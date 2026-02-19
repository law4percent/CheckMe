import cv2
import numpy as np

from .logger import get_log_file

log = get_log_file("smart_collage.log")

class SmartCollage:

    def __init__(self, img_paths: list[str]) -> None:
        self.img_paths = img_paths

    def _determine_grid(self, count: int):
        """
        Returns (cols, rows) based on number of images.
        Supports more than 6 images by auto-expanding grid.
        """

        if count == 1:
            return 1, 1
        elif count == 2:
            return 2, 1
        elif count in [3, 4]:
            return 2, 2
        elif count in [5, 6]:
            return 3, 2
        elif count in [7, 8, 9]:
            return 3, 3
        else:
            log(f"Found {count} images. Using dynamic grid with 3 columns and {int(np.ceil(count / 3))} rows. This may result in a very tall collage.", type="warning")
            cols = 3
            rows = int(np.ceil(count / 3))
            return cols, rows

    def _resize_with_aspect_ratio(self, img, target_w, target_h):
        """
        Resize image preserving aspect ratio and pad with white background.
        """

        h, w = img.shape[:2]

        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        canvas = np.full((target_h, target_w, 3), 255, dtype=np.uint8)

        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2

        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    def _add_label(self, img, label_text):
        """
        Burn PAGE_X label in top-left with dynamic scaling.
        """
        h, w = img.shape[:2]

        # Calculate scale factors based on image width
        # 0.002 is a "magic number" that keeps font proportional
        font_scale = w * 0.0015 
        thickness = max(1, int(w * 0.003))
        
        # Determine text size to make the background box fit perfectly
        (text_w, text_h), baseline = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )

        # Create a dynamic box with padding
        padding = int(w * 0.01)
        box_w = text_w + (padding * 2)
        box_h = text_h + (padding * 2)

        # Draw the white background box
        cv2.rectangle(img, (0, 0), (box_w, box_h), (255, 255, 255), -1)
        
        # Draw the black text
        # text_h is used for the y-coordinate to offset from top
        cv2.putText(
            img, label_text, (padding, text_h + padding), 
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness, cv2.LINE_AA
        )

        return img

    def create_collage(self, sheet_width=2480, aspect_ratio=1.41, gutter_size=40) -> np.ndarray | None:
        """
        Creates a collage based on standard paper dimensions (e.g., A4).
        sheet_width: 2480px is standard for A4 at 300 DPI.
        aspect_ratio: 1.41 for A4, 1.29 for US Letter.
        """
        images = [cv2.imread(p) for p in self.img_paths if cv2.imread(p) is not None]
        if not images: return None

        cols, rows = self._determine_grid(len(images))
        
        # Define the size of one 'paper' slot
        slot_w = sheet_width
        slot_h = int(sheet_width * aspect_ratio)

        processed_imgs = []
        for i, img in enumerate(images):
            # Resize the actual image to fit the paper slot
            # This prevents the 'shrunk' look by giving it plenty of pixel room
            res = self._resize_with_aspect_ratio(img, slot_w, slot_h)
            res = self._add_label(res, f"PAGE_{i+1}")
            
            # Add a small border around each sheet to simulate paper edges
            res = cv2.copyMakeBorder(res, gutter_size, gutter_size, gutter_size, gutter_size, 
                                    cv2.BORDER_CONSTANT, value=[200, 200, 200]) # Light grey gutter
            processed_imgs.append(res)

        # Fill empty slots if necessary
        blank_sheet = np.full((slot_h + 2*gutter_size, slot_w + 2*gutter_size, 3), 255, dtype=np.uint8)
        while len(processed_imgs) < (rows * cols):
            processed_imgs.append(blank_sheet)

        # Stack the rows and columns
        grid_rows = [cv2.hconcat(processed_imgs[r*cols : (r+1)*cols]) for r in range(rows)]
        final_collage = cv2.vconcat(grid_rows)

        return final_collage

    def save(self, raw_collage: np.ndarray, output_path: str) -> None:
        """Saves the collage with maximum compression for PNG format."""
        cv2.imwrite(output_path, raw_collage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])


# --- Usage Example ---
if __name__ == "__main__":

    paths = [
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
        "../scans/answer_sheets/images/assess_001.jpg",
    ]

    collage_builder = SmartCollage(paths)
    collage = collage_builder.create_collage()


    if collage is not None:
        # Option 1: Save as PNG with maximum compression (tested and recommended)
        collage_builder.save(collage, "final_collage.png")

        # Option 2: Save as JPEG with high quality (not recommended due to artifacts)
        # gray_collage = cv2.cvtColor(collage, cv2.COLOR_BGR2GRAY)
        # cv2.imwrite("final_collage.jpg", gray_collage)
        

        # getstring = get_base64_from_opencv(collage)
        # with open("collage_base64.txt", "w") as f:
        #     f.write(getstring)

        print("Collage generated and saved successfully.")
    else:
        print("Collage generation failed.")
