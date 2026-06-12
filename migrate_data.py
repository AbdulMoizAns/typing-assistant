"""
migrate_data.py - Run this ONCE to fix trailing spaces in all JSON data files.
"""
import json
import os
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def clean_data(data):
    if isinstance(data, dict):
        return {
            k.strip(): clean_data(v) if isinstance(v, (dict, list)) else (v.strip() if isinstance(v, str) else v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [clean_data(item) if isinstance(item, (dict, list)) else (item.strip() if isinstance(item, str) else item) for item in data]
    return data

def migrate():
    json_files = glob.glob(os.path.join(BASE_DIR, "*.json"))
    for filepath in json_files:
        print(f"Cleaning {os.path.basename(filepath)}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cleaned_data = clean_data(data)
            
            clean_filepath = filepath.strip()
            if filepath != clean_filepath:
                os.rename(filepath, clean_filepath)
                filepath = clean_filepath
                
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
            print(f"  -> Successfully cleaned and saved.")
        except Exception as e:
            print(f"  -> Error processing {filepath}: {e}")

if __name__ == "__main__":
    migrate()
    print("\nMigration complete! You can now run alpha_assistant.py.")
