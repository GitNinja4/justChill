# Aditya & Tishu

A private-feeling, single-page long-distance space served by FastAPI. It has live Delhi/Sydney clocks, a database-backed WebSocket chat, sentence-based sign-in for Aditya and Tishu, persistent reactions, and authorized message deletion. Local development uses SQLite by default; Render uses PostgreSQL.

## Run it on your computer

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/).
2. Open a terminal in this folder and run `py -m venv .venv`.
3. Activate it with `.venv\Scripts\activate` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux.
4. Install the app packages with `python -m pip install -r requirements.txt`.
5. (Optional) Set `DATABASE_URL` to use PostgreSQL locally; otherwise the app creates `data/relationship.sqlite3`. Set each person's WhatsApp phone number in international format without `+`, spaces, or punctuation: `$env:ADITYA_WHATSAPP_NUMBER="919334823399"` and `$env:TISHU_WHATSAPP_NUMBER="61412345678"` in PowerShell, or export the corresponding variables on macOS/Linux. The call button targets the other person's number; without a configured number, it stays disabled.
6. Start the app with `python -m uvicorn app:app --reload`.
7. Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The SQLite database is created at `data/relationship.sqlite3`.
8. Sign in with `I'm Aditya` or `I'm Tishu`, then open **My little corner** and change the starter sentence to a private phrase of at least 8 characters.

## Deploy free on Render

1. Create a [GitHub account](https://github.com/) if you do not already have one, then create a new repository. In this project folder, run `git init`, `git add .`, `git commit -m "Build Aditya and Tishu app"`, and push the repository to GitHub. GitHub's page for a new repository shows the exact commands for connecting an existing folder.
2. Create a [Render account](https://render.com/) and connect it to GitHub.
3. In Render, choose **New +**, then **Blueprint**. Select the GitHub repository containing this project. Render detects `render.yaml` and prepares the web service and a private PostgreSQL database.
4. When asked for `ADITYA_WHATSAPP_NUMBER` and `TISHU_WHATSAPP_NUMBER`, enter each person's number in international format with digits only (for example, `919334823399`). These configure the call button; they are not login credentials.
5. Review the database plan and its price in Render before applying the Blueprint. The database uses the smallest paid Render Postgres plan so chat history does not expire with the free database tier.
6. Back up any existing messages from the currently running SQLite deployment before syncing the PostgreSQL configuration. The app does not automatically copy existing SQLite data into PostgreSQL.
7. Apply the Blueprint and wait for the database and service to finish deploying. Open the `onrender.com` URL Render gives you. Update `CORS_ORIGINS` in `render.yaml` to that exact URL if Render assigned a different subdomain, then commit and push the change to redeploy.
8. Open the URL and sign in with `I'm Aditya` or `I'm Tishu`. Each person should open **My little corner** and change their starter sentence to a private phrase of at least 8 characters, then share the URL with each other.

### Database and storage

The Render Blueprint provisions a paid Postgres database and injects its private connection URL as `DATABASE_URL`. The web service can remain on its free plan; database charges are separate. Render's free Postgres databases expire after 30 days and do not include backups, so this Blueprint does not use the free database plan. Local SQLite data is not automatically migrated when changing databases. Back up any existing production data before syncing a database change.

The page itself, REST API, and WebSocket are served by the same FastAPI service. No separate frontend hosting or external database is needed. A person's sign-in session determines their chat name and which WhatsApp number the call button targets.

Messages, deletion state, reactions, sessions, sign-in hashes, and the shared welcome sentence are stored in the database. Existing databases are upgraded on startup with the message deletion, reactions, and settings tables/columns. Message deletion is a server-authorized soft delete: the original text is cleared and the other connected client receives the deleted state.

## Sign-in notes

The starter sentences are public examples, not private credentials. Change them before relying on the deployed app for privacy. New and upgraded sign-in values use Argon2id hashes; older PBKDF2 hashes are upgraded automatically on the next successful login. The app never stores the sentence itself and uses an HttpOnly browser session cookie. There is no email recovery: if a sentence is forgotten, reset that person's row in the `sign_in_phrases` table in the SQLite database or restore a database backup. Anyone with the URL can see the sign-in screen, but needs the sentence to access chat.

The current chat is protected by authenticated transport and database access, but it is **not genuine end-to-end encryption**: the FastAPI server currently receives message text so it can validate and store it. Do not describe the deployed app as E2EE until a client-key design using an established protocol/library is added and tested. A future E2EE implementation should replace the message `text` field with ciphertext and keep decryption keys exclusively on the two clients.