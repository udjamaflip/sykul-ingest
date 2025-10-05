# ────────────────────────────────────────────────────────────────────────────────
#  strava-runtime.py
#  --------------------------------------------------------------------
#  * Uses StravaConnector (src/cli/connectors/strava.py)
#  * Handles OAuth + token refresh
#  * Exposes a tiny Flask endpoint (`/continue`) for the callback
#  * On start, prints the profile and last 25 activities
#  --------------------------------------------------------------------
# ────────────────────────────────────────────────────────────────────────────────
import json, os, time
from flask import Flask, request, redirect
from strava import StravaConnector
import requests

# ---------------------------------------------------------------------------
# Config – adjust as needed
# ---------------------------------------------------------------------------
TOKEN_FILE   = "./data/strava_token.json"   # where the refresh_token lives
PROFILE_FILE = "./data/profile.json"
ACTIVITIES_FILE = "./data/activities_last25.json"

CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID", "161605")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "e09397a23f8059450e01067c83bc94155ccfa9ce")
REDIRECT_URI  = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:5000/continue")

AUTH_URL      = (
    f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=profile:read_all,activity:read_all"
)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# 1️⃣  Utility helpers
# ---------------------------------------------------------------------------
def load_tokens() -> dict | None:
    """Return token dict or None if the file doesn't exist."""
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_tokens(data: dict) -> None:
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def refresh_token(refresh: str) -> dict:
    """Call Strava to exchange a refresh token for a new access token."""
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        },
    )
    resp.raise_for_status()
    new = resp.json()
    write_tokens(new)          # persist the new token bundle
    return new

def get_current_token() -> str | None:
    """Return a valid access token, refreshing if necessary."""
    t = load_tokens()
    if not t:
        return None
    # If the token is still valid (Strava tokens live 1 hour, we add a safety margin)
    # Strava does not provide expiry in the refresh flow, so we always refresh.
    return refresh_token(t["refresh_token"])["access_token"]

# ---------------------------------------------------------------------------
# 2️⃣  OAuth callback – “continue” endpoint
# ---------------------------------------------------------------------------
@app.route("/continue")
def continue_oauth():
    """
    Strava redirects here after the user authorises the app.
    We exchange the code for a token bundle and store it.
    """
    code = request.args.get("code")
    if not code:
        return "Missing code parameter", 400

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    token_data = resp.json()
    write_tokens(token_data)
    return "Strava authentication successful. You can close this window."

# ---------------------------------------------------------------------------
# 3️⃣  Main sync routine (profile + last 25 activities)
# ---------------------------------------------------------------------------
def sync():
    token = get_current_token()
    if not token:
        print("[SYNC] No access token. Visit the link below to authorise:")
        print(AUTH_URL)
        return
    connector = StravaConnector(token)

    # 3.1  Profile
    profile = connector.fetch_profile()
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    print("[SYNC] Profile saved to", PROFILE_FILE)

    # 3.2  Last 25 activities
    activities = connector.fetch_activities_with_details(per_page=25)
    for (i, activity) in enumerate(activities):
        
        print(activity['id'], activity['name'], activity['type'])

    with open(ACTIVITIES_FILE, "w", encoding="utf-8") as f:
        json.dump(activities, f, indent=2)
    print("[SYNC] Last 25 activities saved to", ACTIVITIES_FILE)

# ---------------------------------------------------------------------------
# 4️⃣  If run as a script, start Flask and perform an initial sync
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run the sync once on start
    sync()

    # Start the tiny Flask server to listen for the OAuth callback
    print("[FLASK] Listening for OAuth callback on", REDIRECT_URI)
    app.run(host="0.0.0.0", port=5000)