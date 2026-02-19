from googleapiclient.discovery import build
from auth import get_credentials
import argparse

def check_storage(profile_name):
    print(f"Checking storage for {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)

    try:
        about = service.about().get(fields='storageQuota').execute()
        quota = about.get('storageQuota', {})
        
        limit = int(quota.get('limit', 0))
        usage = int(quota.get('usage', 0))
        usage_drive = int(quota.get('usageInDrive', 0))
        usage_trash = int(quota.get('usageInDriveTrash', 0))
        
        def sizeof_fmt(num, suffix="B"):
            for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
                if abs(num) < 1024.0:
                    return f"{num:3.1f}{unit}{suffix}"
                num /= 1024.0
            return f"{num:.1f}Pi{suffix}"

        print("\n" + "="*40)
        print(f"STORAGE REPORT: {profile_name}")
        print("="*40)
        print(f"Total Limit: {sizeof_fmt(limit)}")
        print(f"Total Used:  {sizeof_fmt(usage)} ({(usage/limit)*100:.1f}%)")
        print("-" * 20)
        print(f"Drive Usage: {sizeof_fmt(usage_drive)}")
        print(f"Trash Usage: {sizeof_fmt(usage_trash)}")
        print(f"Other (Gmail/Photos): {sizeof_fmt(usage - usage_drive - usage_trash)}")
        print("="*40)

    except Exception as e:
        print(f"Error checking storage: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check Google Storage Quota.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    args = parser.parse_args()
    
    check_storage(args.profile)
