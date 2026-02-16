import requests
import json
import mimetypes
import os

def upload_and_process_http(api_key, image_path, prompt):
    # 1. PREPARE FILE
    mime_type, _ = mimetypes.guess_type(image_path)
    file_size = os.path.getsize(image_path)
    
    # 2. UPLOAD FILE (The "Staging" Step)
    # Endpoint: /upload/v1beta/files
    upload_url = "https://generativelanguage.googleapis.com/upload/v1beta/files"
    
    upload_headers = {
        "x-goog-api-key": api_key,
        "X-Goog-Upload-Protocol": "multipart",
    }
    
    # Metadata part of the multipart request
    metadata = {"file": {"display_name": os.path.basename(image_path)}}
    
    files = {
        'metadata': (None, json.dumps(metadata), 'application/json'),
        'file': (os.path.basename(image_path), open(image_path, 'rb'), mime_type)
    }

    print(f"Uploading {image_path} via HTTP...")
    upload_response = requests.post(upload_url, headers=upload_headers, files=files)
    upload_response.raise_for_status()
    
    file_info = upload_response.json()
    file_uri = file_info['file']['uri'] # This is the "reference" to your cloud file

    # 3. GENERATE CONTENT (The "Inference" Step)
    # Use the regular generateContent endpoint but reference the URI
    gen_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    gen_payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"file_data": {"mime_type": mime_type, "file_uri": file_uri}}
            ]
        }]
    }
    
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    
    print("Generating content...")
    response = requests.post(f"{gen_url}", headers=headers, json=gen_payload)
    response.raise_for_status()
    
    return response.json()['candidates'][0]['content']['parts'][0]['text']