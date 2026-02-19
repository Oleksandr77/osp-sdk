import os
import shutil
import re

SOURCE_DIR = "../../../10_Business_Admin/Telegram_Export/Documents"
BASE_DIR = "../../../10_Business_Admin/Telegram_Export"

CATEGORIES = {
    "Finance": {
        "keywords": ["invoice", "faktura", "statement", "wyciąg", "swift", "pko", "bank", "trans", "zestawienie", "rachunek", "opłata", "salary", "koszt"],
        "extensions": [".pdf", ".csv", ".xlsx", ".xls"]
    },
    "Legal": {
        "keywords": ["umowa", "contract", "agreement", "krs", "nip", "regon", "statut", "uchwała", "protokół", "decyzja", "sąd", "wyrok", "pełnomocnictwo"],
        "extensions": [".pdf", ".docx", ".doc"]
    },
    "Projects": {
        "keywords": ["spec", "projekt", "wytyczne", "wymagania", "brief", "plan", "roadmap"],
        "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"]
    },
    "Media": {
        "keywords": [],
        "extensions": [".jpg", ".jpeg", ".png", ".mp4", ".mov"]
    }
}

def organize():
    # Create category dirs
    for cat in CATEGORIES:
        os.makedirs(os.path.join(BASE_DIR, cat), exist_ok=True)
    
    # Create 'Other' dir
    os.makedirs(os.path.join(BASE_DIR, "Other"), exist_ok=True)

    if not os.path.exists(SOURCE_DIR):
        print(f"Source directory {SOURCE_DIR} does not exist.")
        return

    files_moved = 0
    for filename in os.listdir(SOURCE_DIR):
        file_path = os.path.join(SOURCE_DIR, filename)
        if not os.path.isfile(file_path):
            continue

        name_lower = filename.lower()
        _, ext = os.path.splitext(name_lower)
        
        target_cat = "Other"
        
        # Check categories
        for cat, rules in CATEGORIES.items():
            # Check extensions first if strictly defined
            if rules["extensions"] and ext in rules["extensions"]:
                # If keywords defined, check them too. If not, extension is enough (like Project archives or Media)
                if not rules["keywords"]: 
                    target_cat = cat
                    break
                else:
                    if any(k in name_lower for k in rules["keywords"]):
                        target_cat = cat
                        break
            # If extension matches but keywords don't, it might fall through.
            # But specific keywords often override extension (e.g. invoice.pdf vs contract.pdf).
            
            # Correction: Logical flow
            # 1. Check keywords. If keyword match -> Assign Category (regardless of extension? or check extension compatibility?)
            # Let's prioritize keywords.
            if any(k in name_lower for k in rules["keywords"]):
                target_cat = cat
                break

        # Fallback for Media/Projects based purely on extension if no keyword matched
        if target_cat == "Other":
             for cat, rules in CATEGORIES.items():
                if not rules["keywords"] and ext in rules["extensions"]:
                     target_cat = cat
                     break

        target_path = os.path.join(BASE_DIR, target_cat, filename)
        shutil.move(file_path, target_path)
        files_moved += 1
        print(f"Moved {filename} -> {target_cat}/")

    print(f"Organized {files_moved} files.")
    
    # Clean up empty source dir
    # os.rmdir(SOURCE_DIR) 

if __name__ == "__main__":
    organize()
