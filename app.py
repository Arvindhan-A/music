import os
import time
import secrets
import urllib.parse

import requests
from flask import (
    Flask, redirect, request, session,
    jsonify, render_template, url_for
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID", "5fafe0449f234af48e4f6f831c5f46df")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI  = "https://music.gaiasentinel.online/callback"

SCOPES = (
    "streaming "
    "user-read-email "
    "user-read-private "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "playlist-read-private "
    "playlist-read-collaborative"
)


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    connected = "access_token" in session
    error     = request.args.get("error", "")
    return render_template("index.html", connected=connected, error=error)


# ── OAuth flow ─────────────────────────────────────────────────────────────────

@app.route("/login")
def login():
    if not CLIENT_ID:
        return "SPOTIFY_CLIENT_ID is not set in .env", 500

    state = secrets.token_hex(16)
    session["oauth_state"] = state

    params = {
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPES,
        "state":         state,
        "show_dialog":   "false",
    }
    return redirect(
        "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    )


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return redirect("/?error=" + urllib.parse.quote(error))

    code  = request.args.get("code", "")
    state = request.args.get("state", "")

    if state != session.pop("oauth_state", None):
        return redirect("/?error=state_mismatch")

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
            "client_id":    CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    data = resp.json()

    if "access_token" not in data:
        msg = data.get("error_description", data.get("error", "unknown"))
        return redirect("/?error=" + urllib.parse.quote(msg))

    session["access_token"]     = data["access_token"]
    session["refresh_token"]    = data.get("refresh_token", "")
    session["token_expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    session.permanent = True          # survive browser close

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ── Token API (called by frontend JS) ─────────────────────────────────────────

@app.route("/api/token")
def api_token():
    """Return the current access token, refreshing it if needed."""
    if "access_token" not in session:
        return jsonify({"error": "not_connected"}), 401

    if time.time() > session.get("token_expires_at", 0):
        ok = _do_refresh()
        if not ok:
            session.clear()
            return jsonify({"error": "token_expired"}), 401

    return jsonify({
        "access_token": session["access_token"],
        "connected":    True,
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    ok = _do_refresh()
    if ok:
        return jsonify({"access_token": session["access_token"]})
    session.clear()
    return jsonify({"error": "refresh_failed"}), 401


def _do_refresh() -> bool:
    rt = session.get("refresh_token")
    if not rt:
        return False

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": rt,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    data = resp.json()
    if "access_token" not in data:
        return False

    session["access_token"]     = data["access_token"]
    session["token_expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    if "refresh_token" in data:            # Spotify may rotate the refresh token
        session["refresh_token"] = data["refresh_token"]
    return True


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5050)
