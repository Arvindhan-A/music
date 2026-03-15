# Pomodoro × Spotify — music.gaiasentinel.online

## Quick-start

### 1. Spotify Developer Setup (one-time)

1. Go to https://developer.spotify.com/dashboard → **Create app**
2. Name it anything (e.g. "GaiaSentinel Pomodoro")
3. Under **Redirect URIs**, add **exactly**:
   ```
   https://music.gaiasentinel.online/callback
   ```
4. Save. Copy your **Client ID** and **Client Secret**.

---

### 2. Server Setup

```bash
# Clone / copy files to your server
cd /home/gaia
git clone <your-repo> pomodoro   # or scp the folder

cd pomodoro

# Python virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env
nano .env          # fill in CLIENT_ID, CLIENT_SECRET, SECRET_KEY
```

---

### 3. Systemd service

```bash
sudo cp pomodoro.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pomodoro
sudo systemctl start pomodoro
sudo systemctl status pomodoro   # should say "active (running)"
```

---

### 4. Nginx

```bash
sudo cp music.gaiasentinel.online.nginx /etc/nginx/sites-available/music.gaiasentinel.online
sudo ln -s /etc/nginx/sites-available/music.gaiasentinel.online /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

SSL (if not using Cloudflare proxy):
```bash
sudo certbot --nginx -d music.gaiasentinel.online
```

---

### 5. Cloudflare DNS

| Type | Name  | Content           | Proxy  |
|------|-------|-------------------|--------|
| A    | music | <your server IP>  | ✅ On  |

---

## How OAuth works (no more INVALID_CLIENT)

The redirect URI is hardcoded in `app.py`:
```python
REDIRECT_URI = "https://music.gaiasentinel.online/callback"
```
Flask handles the OAuth callback server-side using your **Client Secret** — the secret never touches the browser. Tokens are stored in the Flask session (server-side cookie).

**Flow:**
1. User clicks "Connect with Spotify" → `/login`
2. Flask redirects to Spotify with the exact redirect URI above
3. Spotify sends the code back to `/callback`
4. Flask exchanges it for tokens (using Client Secret) → stores in session
5. User lands back on `/` with Spotify connected
6. Frontend fetches `/api/token` to get the access token for API calls
7. Token auto-refreshes every ~50 minutes

---

## File structure

```
pomodoro/
├── app.py                          ← Flask backend (OAuth + token API)
├── templates/
│   └── index.html                  ← Full React frontend
├── requirements.txt
├── .env                            ← secrets (never commit this)
├── .env.example                    ← template
├── Procfile                        ← gunicorn entry point
├── pomodoro.service                ← systemd unit
└── music.gaiasentinel.online.nginx ← nginx vhost
```

---

## Logs

```bash
# App logs
tail -f /home/gaia/pomodoro/error.log

# Systemd
journalctl -u pomodoro -f
```
