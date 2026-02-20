def main() -> None:
    """
    Prequisite:
    - Raspi should be connected to the internet
    - L3210-Scanner should be connected to the Raspi and ready to scan the answer sheets
    - The system should have access to the Cloudinary and Gemini API for uploading images and extracting data from the images
    - The system should have access to the RTDB for saving and retrieving data such as Answer Key, Assessment UID, and Student's Score
    - Keypad 3x4
    
    Services:
    - firebase_rtdb_client.py 
    - gemini_client.py 
    - image_uploader.py 
    - keypad_hardware.py 
    - l3210_scanner.py 
    - lcd_hardware.py 
    - logger.py 
    - prompts.py 
    - sanitizer.py 
    - scorer.py 
    - smart_collage.py 
    - utils.py


    STEP 1: Auth/User Verification
    [] Description: System will check the cred.txt and check the details for {teacher_uid} and {username}.
        [] - IF the system cannot find the the cred.txt THEN it will make new one cred.txt file and return {NOT_AUHTENTICATED}.
        [] - IF the system found the cred.txt THEN it will extract the data on it as dict type and check for the keys such as {teacher_uid} and {username}.
        [] - IF the require keys exist THEN the system will check the values.
        [] - IF the values were checked as None THEN system returns {NOT_AUHTENTICATED} ELSE returns {AUTHENTICATED} and {teacher_uid.value} and {username.value}.
    
    [] System will check if AUTHENTICATED or NOT_AUTHENTICATED.
        [] - IF the system confirmed AUTHENTICATED THEN will proceed to STEP 2 ELSE will proceed back to STEP 1

    STEP 2: Home Options Display
    [] System will ask to user to pick one options in Home.
    
        Sample options to display:
            Options
            [1] Scan new Ans Key
            [2] Start checking Ans Sheets
            [3] Settings
    
        STEP 2.A: Scan new Ans Key
        [] System will ask the exact number of the questions and initially save the data to variable {exact_number_of_questions}
        [] System will ask to user to pick one option (LOOP)
            Sample options to display:
                Options
                [1] Scan
                [2] Done and Save
                [3] Cancel
            
            FLOW:
                [1] Scan
                    - System will trigger the L3210-Scanner and will wait 10s for the next step to avoid double-clicked
                    - Then after 10s, display Scanning Page {n} (incremental n) while waiting to L3210-Scanner to finish...
                    - After finish collecting the scanned file name and append it into the list
                    - Then redirect to the STEP 2.A base

                [2] Done and Save
                    - Try to upload the list of local scanned images into the Cloudinary, and collect the return uploaded images' URLs as List
                    - IF success to upload all the images, 
                        - THEN check the length of list and IF it's greater than 1, collage the local scanned images else do nothing
                        - THEN send the image to gemini by pick client type such as sdk or http
                        - THEN save the {image_URLs}, {extracted_assessment_uid}, {extracted_answer_key}, and {exact_number_of_question} to the RTBD
                    
                    - ELSE, 
                        -THEN tell the user that uploading images was failed AND display options
                                Sample options to display:
                                    Options
                                    [1] Re-upload
                                    [2] Exit

                            FLOW:
                                [1] Re-upload
                                    - Repeat the procees of [2] Done and Save

                                [2] Exit
                                    - Discard all the data from local AND delete the scanned local images
                                    - Then redirect to the base such as STEP 2
                    
                [3] Cancel
                    - Discard all the data from local AND delete the scanned local images
                    - Then redirect to the base such as STEP 2
                
        STEP 2.B: Start checking Ans Sheets
            [] IF the systems found out there are no any list of Answer Key from RTDB, 
                - THEN notify the Teacher to proceed with option 1 first
            [] ELSE get the {extracted_assessment_uid}, {extracted_answer_key}, and {exact_number_of_question} from RTDB
                - THEN display options
                    Sample options to display:
                        Options
                        [1] Scan
                        [2] Done and Save
                        [3] Cancel

                        
                    FLOW:
                        [1] Scan
                            - System will trigger the L3210-Scanner and will wait 10s for the next step to avoid double-clicked
                            - Then after 10s, display Scanning Page {n} (incremental n) while waiting to L3210-Scanner to finish...
                            - After finish collecting the scanned file name and append it into the list
                            - Then redirect to the STEP 2.B base

                        [2] Done and Save
                            - Try to upload the list of local scanned images into the Cloudinary, and collect the return uploaded images' URLs as List
                            - IF not {is_gemini_task_done}:
                                - Check the length of list and IF it's greater than 1, collage the local scanned images else do nothing
                                - Send the image to gemini by picking the client type such as sdk or http
                                - IF extraction OCR with gemini was success,
                                    - THEN save the {is_final_score}, {total_score}, {extracted_student_id}, {extracted_assessment_uid}, {extracted_answer_sheet}, and {exact_number_of_question} to the RTBD
                                - {is_gemmini_task_done} = True
                                - IF gemini failed and no more retry for gemini,
                                    - THEN show warning to the teacher like:
                                        "Gemini out of quota, cannot process the image for now, please try again later"
                                        "Gemini failed to extract the image, please try again"
                                        "Gemini OCR has problem, please try again"
                                        - In short, this will warning base on the health of the gemini and the error message from gemini
                                        - THEN redirect to the base such as STEP 2.B
                                    
                            - IF success to upload all the images in cloudinary,
                                - THEN save the {image_URLs} to RTDB
                                - THEN just inform the Teacher that has done to upload and {total_score}/{exact_number_of_questions} 
                                - THEN show other option:
                                    Sample options to display:
                                        Options
                                        [1] Next sheet
                                        [2] Exit

                                    FLOW:
                                        [1] Next sheet
                                            - Discard all the data from local AND delete the scanned local images

                                        [2] Exit
                                            - Just go back to the base such as STEP 2 
                            
                            - ELSE, 
                                -THEN tell the teacher that uploading images was failed AND display options
                                    Sample options to display:
                                        Options
                                        [1] Re-upload
                                        [2] Discard warning and proceed to the next sheet
                                        [3] Exit
                                        
                                    FLOW:
                                        [1] Re-upload
                                            - Repeat the procees of [2] Done and Save

                                        [2] Discard warning and proceed to the next sheet
                                            - Discard all the data from local AND run a backgound process to reupload the images to cloudinary, use multiprocessing to do this in the background, and then just proceed to the next sheet
                                            - In the background processing, add three attempts to re-upload the images to cloudinary if it's failed then delete the local scanned images and just save the {image_URLs} as empty list in RTDB
                                        
                                        [3] EXIT
                                            - Just go back to the base such as STEP 2
                            
                        [3] Cancel
                            - Discard all the data from local AND delete the scanned local images
                            - Then redirect to the base such as STEP 2
    """