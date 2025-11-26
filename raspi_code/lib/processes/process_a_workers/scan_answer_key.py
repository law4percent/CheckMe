import cv2
import time
import hardware
import display
from datetime import datetime

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

def combine_now(images_names: list) -> None:
    """
        Best grid
        1 pic   = 1x1
        2 pics  = 1x2
        3 pics  = 2x2 (blank image for the 4th)
        4 pics  = 2x2
        5 pics  = 2x3 (blank image for the 6th)
        6 pics  = 2x3
        7 pics  = 3x3 (blank images for the 8th and 9th)
        8 pics  = 3x3 (blank images for the 9th)
        9 pics  = 3x3
    """
    pass


def save_scan_answer_key(frame: any, img_path: str) -> str:
    # Process A will handle:
    # save the image file detail into RTDB
    # save to local storage ✅
    # every answer key, once scanned, this will generate new .txt file in credentials folder (assessmentUid.txt)
    
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_name = f"{img_path}/captured_{timestamp}.jpg"
    cv2.imwrite(img_name, frame)
    print(f"Image saved as {img_name}")
    time.sleep(0.5)
    return img_name


def run(rows: any, cols: any, camera_index: int, save_logs: bool, show_windows: bool, answer_key_path: str) -> None:
    capture = cv2.VideoCapture(camera_index)

    collected_image_names = []
    number_of_sheets, count_sheet, is_answered_number_of_sheets  = [1, 1, False]
    essay_existence , is_answered_essay_existence   = [False, False]

    if not capture.isOpened():
        print("Error - Cannot open camera")
        exit()

    while True:
        time.sleep(0.1)
        key = hardware.read_keypad(rows, cols)

        if not is_answered_number_of_sheets:
            print("How many sheets?")
            if key != None and key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                number_of_sheets = int(key)
                is_answered_number_of_sheets = True
            continue

        if not is_answered_essay_existence:
            print("Is there an essay?")
            if key != None and key in ['1', '2']:
                if key == '1':
                    essay_existence = True
                elif key == '2':
                    essay_existence = False
                is_answered_essay_existence = True
            continue
    
        ret, frame = capture.read()
        # display.display_the_options()
        
        if not ret:
            print("Error - Check the camera")
            continue

        if number_of_sheets == 1:
            if key != None:
                if key == display.ScanAnswerKeyOption.SCAN.value:
                    save_scan_answer_key(frame, answer_key_path)
                    print("Scan done...")
                    return
                elif key == display.ScanAnswerKeyOption.EXIT.value:
                    return
        elif number_of_sheets > 1:
            if count_sheet == number_of_sheets:
                print(f"Combining all the {count_sheet} images.. please wait this takes few minutes.")
                combine_now(collected_image_names)
                print(f"Successfully combine all the {count_sheet} images.")
                return
            
            extension = ''
            if count_sheet > 3:
                extension = 'th'
            elif count_sheet == 3:
                extension = 'rd'
            elif count_sheet == 2:
                extension = 'nd'
            elif count_sheet == 1:
                extension = 'st'
            print(f"Put the {count_sheet}{extension} sheet")

            if key != None:
                if key == display.ScanAnswerKeyOption.SCAN.value:
                    image_name = save_scan_answer_key(frame, answer_key_path)
                    collected_image_names.append(image_name)
                    print(f"Scan {count_sheet}{extension} page done.")
                    count_sheet += 1
                elif key == display.ScanAnswerKeyOption.EXIT.value:
                    print(f"Error - This part becomes true, therefore the combination {number_of_sheets} was failed!")
                    return
        
        if show_windows:
            cv2.imshow("CheckMe-ScanAnswerSheet", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()