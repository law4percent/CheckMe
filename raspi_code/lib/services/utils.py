import os

def path_existence_checkpoint(target_path: str) -> dict:
    if not os.path.exists(target_path):
        return {
            "status"    : "error", 
            "message"   : f"{target_path} is not exist. Source: {__name__}."
        }
    return {"status": "success"}


def file_existence_checkpoint(file_path: str) -> dict:
    if not os.path.isfile(file_path):
        return {
            "status"    : "error", 
            "message"   : f"{file_path} file does not exist. Source: {__name__}."
        }
    return {"status": "success"}