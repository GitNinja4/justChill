# Aditya & chill


A private-feeling, single-page long-distance space served by FastAPI. It has live Delhi/Sydney clocks, a database-backed WebSocket chat, sentence-based sign-in for Aditya and Tishu, persistent reactions, authorized message deletion, and in-app WebRTC audio/video calls. Local development uses SQLite by default; Render uses PostgreSQL.

## Project structure

`app.py` remains the deployment entry point and exports the FastAPI application. Shared backend concerns are being moved into the `server/` package: configuration is in `server/config.py`, database connections are in `server/db.py`, authentication and sessions are in `server/auth.py`, and WebSocket/call state is in `server/realtime.py`. The existing `index.html` still contains the page UI while frontend extraction continues.

## Run it on your computer

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/).
2. Open a terminal in this folder and run `py -m venv .venv`.
3. Activate it with `.venv\Scripts\activate` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux.
4. Install the app packages with `python -m pip install -r requirements.txt`.
5. (Optional) Set `DATABASE_URL` to use PostgreSQL locally; otherwise the app creates `data/relationship.sqlite3`.
6. Start the app with `python -m uvicorn app:app --reload`.
7. Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The SQLite database is created at `data/relationship.sqlite3`.
8. The existing accounts use usernames `aditya` and `tishu`; their starter sign-in phrases are `I'm Aditya` and `I'm Tishu`. Change the starter phrase to a private phrase of at least 8 characters in **My little corner**.
9. Run the focused checks with `python -m unittest discover -s tests -v`.

## Accounts and connections

New users select **Create account**, choose a unique username, set a display name, and create a private sign-in phrase of at least 8 characters. Usernames can be searched exactly and changed once every seven days in **My little corner**; display names can be changed separately. The other person must accept a connection request before a private conversation, letters, or calls are available. A user can have multiple separate one-to-one conversations. Keep the sign-in phrase private because there is no email-based account recovery yet.

## Deploy on Render

1. Create a [GitHub account](https://github.com/) if you do not already have one, then create a new repository. In this project folder, run `git init`, `git add .`, `git commit -m "Build Aditya and Tishu app"`, and push the repository to GitHub. GitHub's page for a new repository shows the exact commands for connecting an existing folder.
2. Create a [Render account](https://render.com/) and connect it to GitHub.
3. Create an external PostgreSQL database on the provider you selected, then keep its SSL connection string ready as a secret. In Render, choose **New +**, then **Blueprint**, and select the GitHub repository containing this project. Render detects `render.yaml` and prepares the free web service; it does not create a database.
4. For reliable calling across restrictive Wi-Fi and mobile networks, optionally configure TURN in the Render service environment; see **In-app calls** below.
5. In the Render service environment, set `DATABASE_URL` to the external provider's SSL connection string. The free web service alone does not make the complete deployment free; the database provider's limits, backups, and retention policy still apply.
6. Back up any existing messages from the currently running SQLite deployment before migrating to PostgreSQL. The app does not automatically copy existing SQLite data into the external database.
7. Apply the Blueprint and wait for the service to deploy. Open the `/health` URL and confirm it returns `{"status":"ok"}`. Open the `onrender.com` URL Render gives you and update `CORS_ORIGINS` in `render.yaml` to that exact URL if Render assigned a different subdomain, then commit and push the change to redeploy.
8. Open the URL and create an account, or sign in to the existing `aditya` / `tishu` account with its current phrase. Existing users should change the starter phrase in **My little corner**. Search for another person's exact username and accept or send a connection request before opening a private conversation.

## In-app calls

Audio and video calls use browser WebRTC. Call setup is relayed through the authenticated chat WebSocket; media is sent directly between browsers when possible. Microphone and camera permissions are requested only after a person starts or answers a call. WebRTC encrypts media in transit; the app does not record calls.

The app includes a public STUN server, which is enough for many networks but not all. For reliable connections across restrictive Wi-Fi and mobile networks, configure a TURN service in the Render web service environment with `CALL_TURN_URLS` (comma-separated TURN URLs), `CALL_TURN_USERNAME`, and `CALL_TURN_CREDENTIAL`. A free web host does not guarantee a free TURN relay. Use restricted client credentials with quotas, not a provider admin secret; these credentials are delivered to the two authenticated clients. Local development can use the STUN fallback.

WebSocket connections are held in the web process's memory, so run one web instance unless shared signaling/pub-sub is added for multiple instances.

Use **Call history** beside the audio/video call buttons to open the scrollable history dialog. It shows the latest 50 calls to both participants, including caller, recipient, mode, time, outcome, and duration. The app stores call metadata only; it does not record media.

## Profile locations

Open **My little corner** and choose **Update my city** to grant the browser one-time location access. The browser rounds coordinates to three decimal places; the app tries Geoapify first when configured, then falls back to OpenStreetMap Nominatim if the first lookup fails. Either provider may receive the approximate point. The app stores only the returned city name and the browser's IANA time zone; coordinates are not stored. Location is not requested on sign-in, and there is no background tracking. Choose **Use default city** to clear the saved locality. Location access requires HTTPS in production (localhost is allowed for development).

Set `GEOAPIFY_API_KEY` in the Render service environment to use Geoapify as the primary provider. Create a project and API key at [Geoapify MyProjects](https://myprojects.geoapify.com/), then add the key as a secret environment variable; it is never sent to the browser. Local development can use the same variable. If it is absent or Geoapify is unavailable, the app falls back to OpenStreetMap Nominatim. The profile credit popup links to Geoapify and OpenStreetMap contributors, as required for Geoapify's free plan.

### Database and storage

The Render Blueprint provisions only the free web service and expects an external PostgreSQL connection string in the `DATABASE_URL` secret. The database provider's charges, limits, backups, and retention policy are separate. Local SQLite data is not automatically migrated when changing databases. Back up any existing production data before syncing a database change. Render Free Web Services have an ephemeral filesystem, so production data must not rely on local SQLite or local uploaded files.

The page itself, REST API, and WebSocket are served by the same FastAPI service. No separate frontend hosting or external database is needed. A person's sign-in session authorizes their chat, attachments, and call signaling.

Messages, deletion state, reactions, letters, profiles, sessions, sign-in hashes, the shared welcome sentence, and uploaded attachment bytes are stored in the database. Chat messages accept up to four images or documents (JPEG, PNG, GIF, WebP, PDF, TXT, or DOCX), up to 10 MB each; a letter can include one image. Attachments are served only to signed-in users. A note can be sent immediately or scheduled in the sender's local time. Scheduled notes appear in the recipient's inbox when due. Opening a note is one-time: it disappears from both participants' lists; replying sends a new note and consumes the original, while closing without replying destroys it. Each person's display name can be changed in **My little corner**; message ownership uses a stable account ID, so renaming does not affect deletion permissions. Existing databases are upgraded on startup with sender IDs, profiles, message deletion, reactions, settings, postcard schema, and attachment metadata. Message deletion is a server-authorized soft delete: the original text is cleared and the other connected client receives the deleted state.

The home page uses a small, locally curated set of rotating greetings. Tishu also gets a time-of-day welcome from a curated set. These messages are generated locally by the app; chat content is not sent to an AI service.

## Sign-in notes

The starter sentences are public examples, not private credentials. Change them before relying on the deployed app for privacy. New and upgraded sign-in values use Argon2id hashes; older PBKDF2 hashes are upgraded automatically on the next successful login. The app never stores the sentence itself and uses an HttpOnly browser session cookie. There is no email recovery: if a sentence is forgotten, reset that person's row in the `sign_in_phrases` table in the SQLite database or restore a database backup. Anyone with the URL can see the sign-in screen, but needs the sentence to access chat.

The current chat is protected by authenticated transport and database access, but it is **not genuine end-to-end encryption**: the FastAPI server currently receives message text so it can validate and store it. Do not describe the deployed app as E2EE until a client-key design using an established protocol/library is added and tested. A future E2EE implementation should replace the message `text` field with ciphertext and keep decryption keys exclusively on the two clients.