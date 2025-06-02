from flask import Blueprint, request
import os
import json
import requests
import hashlib

lastfm_callback = Blueprint("lastfm_callback", __name__)

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
DATA_PATH = os.path.join("data", "lastfm_links.json")

def generate_api_sig(params, secret):
    items = sorted((k, v) for k, v in params.items() if k != "format")
    sig = "".join(f"{k}{v}" for k, v in items)
    sig += secret
    return hashlib.md5(sig.encode("utf-8")).hexdigest()

def save_link(discord_id, session_key, username):
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            links = json.load(f)
    else:
        links = {}
    links[str(discord_id)] = {"session": session_key, "username": username}
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)

@lastfm_callback.route("/api/lastfm/callback")
def lastfm_callback_handler():
    token = request.args.get("token")
    discord_id = request.args.get("discord_id")
    if not token or not discord_id:
        return "Missing token or discord_id", 400

    params = {
        "method": "auth.getSession",
        "api_key": LASTFM_API_KEY,
        "token": token,
        "format": "json"
    }
    api_sig = generate_api_sig(params, LASTFM_API_SECRET)
    params["api_sig"] = api_sig
    resp = requests.get("http://ws.audioscrobbler.com/2.0/", params=params)
    data = resp.json()
    if "session" in data:
        save_link(discord_id, data["session"]["key"], data["session"]["name"])
        return f"✅ Linked Discord ID {discord_id} to Last.fm user {data['session']['name']}! You can now use the bot."
    else:
        return f"❌ Error: {data.get('message', 'Unknown error')}", 400