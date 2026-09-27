# Aditya & Tishu

A private-feeling, single-page long-distance space served by FastAPI. It has live Delhi/Sydney clocks, a SQLite-backed WebSocket chat, and sentence-based sign-in for Aditya and Tishu.

## Run it on your computer

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/).
2. Open a terminal in this folder and run `py -m venv .venv`.
3. Activate it with `.venv\Scripts\activate` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux.
4. Install the app packages with `python -m pip install -r requirements.txt`.
5. (Optional) Set each person's WhatsApp phone number in international format without `+`, spaces, or punctuation: `$env:ADITYA_WHATSAPP_NUMBER="919334823399"` and `$env:TISHU_WHATSAPP_NUMBER="61412345678"` in PowerShell, or export the corresponding variables on macOS/Linux. The call button targets the other person's number; without a configured number, it stays disabled.
6. Start the app with `python -m uvicorn app:app --reload`.
7. Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The SQLite database is created at `data/relationship.sqlite3`.
8. Sign in with `I'm Aditya` or `I'm Tishu`, then open **My little corner** and change the starter sentence to a private phrase of at least 8 characters.

## Deploy free on Render

1. Create a [GitHub account](https://github.com/) if you do not already have one, then create a new repository. In this project folder, run `git init`, `git add .`, `git commit -m "Build Aditya and Tishu app"`, and push the repository to GitHub. GitHub's page for a new repository shows the exact commands for connecting an existing folder.
2. Create a [Render account](https://render.com/) and connect it to GitHub.
3. In Render, choose **New +**, then **Blueprint**. Select the GitHub repository containing this project. Render detects `render.yaml` and prepares a free web service.
4. When asked for `ADITYA_WHATSAPP_NUMBER` and `TISHU_WHATSAPP_NUMBER`, enter each person's number in international format with digits only (for example, `919334823399`). These configure the call button; they are not login credentials.
5. Choose **Apply** and wait for the first deploy to finish. Open the `onrender.com` URL Render gives you. Update `CORS_ORIGINS` in `render.yaml` to that exact URL if Render assigned a different subdomain, then commit and push the change to redeploy.
6. Open the URL and sign in with `I'm Aditya` or `I'm Tishu`. Each person should open **My little corner** and change their starter sentence to a private phrase of at least 8 characters, then share the URL with each other.

### Important free-tier storage note

The Render free web service has an ephemeral filesystem, and free services do not include a persistent disk. This app stores data in SQLite at `./data/relationship.sqlite3`, so it survives normal page refreshes and process activity but can be erased when Render replaces or restarts the service, including deploys or a spin-down. The app remains fully usable on the free tier, but its history is not guaranteed. For durable shared history on Render, attach a persistent disk (paid); alternatively, deploy to a host that offers a persistent volume within its free allowance. Back up `data/relationship.sqlite3` before moving hosts.

The page itself, REST API, and WebSocket are served by the same FastAPI service. No separate frontend hosting or external database is needed. A person's sign-in session determines their chat name and which WhatsApp number the call button targets.

## Sign-in notes

The starter sentences are public examples, not private credentials. Change them before relying on the deployed app for privacy. The app stores salted, slow password hashes rather than the sentences themselves, and uses an HttpOnly browser session cookie. There is no email recovery: if a sentence is forgotten, reset that person's row in the `sign_in_phrases` table in the SQLite database or restore a database backup. Anyone with the URL can see the sign-in screen, but needs the sentence to access chat.