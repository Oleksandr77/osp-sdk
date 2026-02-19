import os
import subprocess
import time

emails = [
    # "a.osadchiy1@gmail.com", # Done
    # "a.osadchyi2014@gmail.com", # Done
    # "bspiritinfo@gmail.com", # Done
    # "economgas2021@gmail.com", # Skipped by user
    # "kovalpl777@gmail.com", # Done
    # "linguaosadchiy@gmail.com", # Skipped by user
    "lobbyst.ua@gmail.com",
    "o82832247@gmail.com",
    # "oneintergroup@gmail.com", # Skipping as we are doing this one separately right now
    "osaleadergmbh@gmail.com",
    "oxanafop2025@gmail.com",
    "smarttv777mibox@gmail.com",
    "uinston1@gmail.com",
    "yourdocua@gmail.com"
]

print("Starting batch authentication for users.")
print("For each user, a browser window will open. Please log in with the corresponding email.")

for email in emails:
    profile = email.split('@')[0]
    print(f"\n--------------------------------------------------")
    print(f"Processing: {email} (Profile: {profile})")
    print(f"--------------------------------------------------")
    
    cmd = f"python3 auth.py --profile {profile}"
    
    # Run the auth command
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"Successfully authenticated {email}")
    except subprocess.CalledProcessError:
        print(f"Failed to authenticate {email}. Moving to next.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        break
    
    input("Press Enter to continue to the next account...")

print("\nBatch process completed.")
