import cv2
import time
from . import hardware
from . import display
from datetime import datetime
import math
import numpy as np

"""
    1. Start (Answer Key option)
    2. The system will ask the user about the number of pages 
    3. The system will ask the user if there is an essay.
    4. Scan/Capture the answer key. (One-by-One) [Put the first page, second page, …, n page]
    5. If the number of pages is greater than 1 THEN
    6. Combine all the images (Applying the combination algorithm)
    7. The system will save the combined images
    8. The system will send the image to Gemini with a prompt (make sure to include in the prompt if there is an essay in the sheet, because if there is, we will apply another algorithm)
"""

def smart_grid_auto(collected_images: list, tile_width: int):
    # 1. Load images
    imgs = [cv2.imread(p) for p in collected_images] # Check the path first and its existence
    imgs = [img for img in imgs if img is not None]
    n = len(imgs)
    
    if n == 0:
        raise ValueError("No valid images provided.")
    
    # 2. Compute grid size
    grid_size = math.ceil(math.sqrt(n))
    rows = grid_size
    cols = grid_size

    # 3. Compute tile size
    tile_height = int(tile_width * 1.4)
    tile_size = (tile_width, tile_height)

    # 4. Resize images
    resized_imgs = []
    for img in imgs:
        resized_imgs.append(cv2.resize(img, tile_size))

    # 5. Fill empty slots with white images
    total_slots = rows * cols
    while len(resized_imgs) < total_slots:
        blank = np.full((tile_height, tile_width, 3), 255, dtype=np.uint8)
        resized_imgs.append(blank)

    # 6. Build grid row by row
    row_list = []
    for r in range(rows):
        start = r * cols
        end = start + cols
        row_imgs = resized_imgs[start:end]
        row_list.append(np.hstack(row_imgs))

    # 7. Combine rows vertically
    combined_image = np.vstack(row_list)
    return combined_image


def combine_images_into_grid(collected_images: list, tile_width: int = 600) -> any:
    combined_image = smart_grid_auto(collected_images, tile_width)
    cv2.imwrite("combined_grid.jpg", combined_image)

    return combined_image


def get_JSON_of_answer_key(image_path: str):
    # 1. Send image to GEMINI
    # 2. Get the JSON
    # 3. Save the JSON as a file answerkeyUid.json
    print()


def save_image_file(frame: any, img_full_path: str):
    # if test_mode:
    #     img_full_path = "images/answer_keys/test.png"
    cv2.imwrite(img_full_path, frame)

def naming_the_file(img_path: str, current_count: int) -> str:
    # Process A will handle:
    # - save to local storage ✅
    # - save the image file detail into RTDB
    # - every answer key, once scanned, this will generate new .txt file in credentials folder (assessmentUid.txt)
    
    # Sample
    # userUid: gbRaC4u7MSRWWRi9LerDQyjVzg22
    # sectionUid: -Obx0gVoVCxQ6QLqOluh
    # subjectUid: -Obx0hwuEsEGlfYboxrN
    # assessmentUid: -1234567890qwertyuiop

    # collectedStudentId:
    # - 4201400
    # - 4201403
    # - 3204423
    # - 2444223

    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{img_path}/img{current_count}.png"


def run(
        task_name           : str,
        keypad_rows_and_cols: list,
        camera_index        : int, 
        save_logs           : bool, 
        show_windows        : bool, 
        answer_key_path     : str, 
        pc_mode             : bool
    ) -> None:

    # ========= TEST KEYS =========
    pc_key = '2' # number of sheets and essay
    # =============================

    rows, cols = keypad_rows_and_cols
    capture = cv2.VideoCapture(camera_index)
    collected_image_names = []
    number_of_sheets, count_page, is_answered_number_of_sheets  = [1, 1, False]
    essay_existence , is_answered_essay_existence   = [False, False]

    if not capture.isOpened():
        print("Error - Cannot open camera")
        exit()

    while True:
        time.sleep(0.1)

        if pc_mode:
            # if not is_answered_number_of_sheets:
            #     print(f"How many sheets? [1-9]: {pc_key}")
            #     time.sleep(2)
            #     if pc_key != None and pc_key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            #         number_of_sheets = int(pc_key)
            #         is_answered_number_of_sheets = True
            #         continue
            #     continue

            # if not is_answered_essay_existence:
            #     print(f"Is there an essay? [1]Y/[2]N: {pc_key}")
            #     time.sleep(2)
            #     if pc_key != None and pc_key in ['1', '2']:
            #         if pc_key == '1':
            #             essay_existence = True
            #         elif pc_key == '2':
            #             essay_existence = False
            #         is_answered_essay_existence = True
            #         print("Analyzing data...✅")
            #         time.sleep(2)
            #         continue
            #     continue

            # print("number_of_sheets:", number_of_sheets)
            # print("essay_existence:", essay_existence)
            continue







        key = hardware.read_keypad(rows = rows, cols = cols)

        if not is_answered_number_of_sheets:
            print("How many pages? [1-9]")
            if key != None and key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                number_of_sheets = int(key)
                is_answered_number_of_sheets = True
                continue
            continue

        if not is_answered_essay_existence:
            print("Is there an essay? [1]Y/[2]N")
            if key != None and key in ['1', '2']:
                if key == '1':
                    essay_existence = True
                elif key == '2':
                    essay_existence = False
                is_answered_essay_existence = True
                print("================")
                print("Analyzing data...")
                time.sleep(1)
                print("number_of_sheets:", number_of_sheets)
                print("essay_existence:", essay_existence)
                print("================")
                time.sleep(2)
                continue
            continue
    
        ret, frame = capture.read()
        if not ret:
            print("Error - Check the camera")
            continue

        # display.display_the_options()
        print("[1] SCAN")
        print("[2] EXIT")

        if show_windows:
            cv2.imshow("CheckMe-ScanAnswerSheet", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if number_of_sheets == 1:
            if key != None and key in ['1', '2']:
                if key == display.ScanAnswerKeyOption.SCAN.value:
                    img_full_path = naming_the_file(img_path=answer_key_path, current_count=count_page)#img_path: str, count_sheet: int, test_mode: bool)
                    save_image_file(frame=frame, img_full_path=img_full_path)
                    get_JSON_of_answer_key() # This is done with GEMINI
                    print("Successfully scanned the answer key...")
                    return
                elif key == display.ScanAnswerKeyOption.EXIT.value:
                    return
                
        elif number_of_sheets > 1:
            extension = ''
            if count_page >= 4:
                extension = 'th'
            elif count_page == 3:
                extension = 'rd'
            elif count_page == 2:
                extension = 'nd'
            elif count_page == 1:
                extension = 'st'
            print(f"Put the {count_page}{extension} page.")

            if key != None and key in ['1', '2']:
                if key == display.ScanAnswerKeyOption.SCAN.value:
                    img_full_path = naming_the_file(img_path=answer_key_path, current_count=count_page)
                    collected_image_names.append(img_full_path)
                    print(f"Scanning the {count_page}{extension} page is done.")
                    
                    if count_page == number_of_sheets:
                        print(f"Combining all the {count_page} images.. please wait this takes few minutes.")
                        print("List of images:", collected_image_names) # Remove this later

                        raw_frame = combine_images_into_grid(collected_image_names)
                        print(f"Combining all the {count_page} images is done.")

                        save_image_file(frame=raw_frame, img_full_path="NOT YET DONE") # NOT YET DONEEEE
                        get_JSON_of_answer_key() # This is done with GEMINI
                        print("Successfully scanned the answer key...")
                        return
                    
                    count_page += 1
                elif key == display.ScanAnswerKeyOption.EXIT.value:
                    print(f"Error - This part becomes true, therefore the combination {number_of_sheets} was failed!")
                    return
    
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()