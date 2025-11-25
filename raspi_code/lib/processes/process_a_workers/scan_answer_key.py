import cv2
import time
import hardware
import display
from datetime import datetime

def save_scan_answer_key(frame: any, img_path: str) -> None:
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
    time.sleep(1)


def run(rows: any, cols: any, camera_index: int, save_logs: bool, show_windows: bool, answer_key_path: str) -> None:
    print("Ready to scan the answer key")
    capture = cv2.VideoCapture(camera_index)

    if not capture.isOpened():
        print("Error - Cannot open camera")
        exit()

    while True:
        time.sleep(0.1)
        ret, frame = capture.read()
        
        display.display_the_options()
        
        key = hardware.read_keypad(rows, cols)
        
        if key != None:
            if key == display.ScanAnswerKeyOption.SCAN.value:
                save_scan_answer_key(frame, answer_key_path)
            elif key == display.ScanAnswerKeyOption.EXIT.value:
                return
        
        if not ret:
            print("Error - Check the camera")
            continue
        
        if show_windows:
            cv2.imshow("CheckMe-ScanAnswerSheet", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    capture.release()
    if show_windows:
        cv2.destroyAllWindows()