# 🔐 Google Workspace Integration Setup

To allow the AI agent to access your Gmail and Google Drive, you need to create a **Google Cloud Project** and generate a `credentials.json` file. This is a one-time setup.

## Step 1: Create a Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** > **New Project**.
3. Name it `Antigravity-Agent` and click **Create**.

## Step 2: Enable APIs
1. In the sidebar, go to **APIs & Services** > **Library**.
2. Search for **Gmail API**, click it, and press **Enable**.
3. Go back to the Library, search for **Google Drive API**, click it, and press **Enable**.

## Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (unless you have a G-Suite organization) and click **Create**.
3. Fill in:
   - **App Name:** Antigravity Agent
   - **User Support Email:** Your email
   - **Developer Contact Info:** Your email
4. Click **Save and Continue** multiple times until finished (you can skip "Scopes" and "Test Users" for now, as you will add yourself as a test user if the app is in "Testing" mode).
5. **Important:** Under **Test Users**, click **Add Users** and add your own Google email address. This authorizes YOU to use the app.

## Step 4: Create Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Application type: **Desktop app**.
4. Name: `Antigravity Client`.
5. Click **Create**.
6. A pop-up will appear. Click **Download JSON** (or the download icon next to the created ID).
7. Save this file as `credentials.json`.

## Step 5: Place the File
Move the `credentials.json` file into this folder:
`/path/to/your/project/integrations/google/`

Once done, run the authentication script to complete the link:
```bash
python integrations/google/auth.py
```
