from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)
STATUS = {
    "main_started": False,
    "token_present": False,
    "database_url_present": False,
    "setup_hook_started": False,
    "db_connected": False,
    "tables_created": False,
    "cogs_loaded": False,
    "discord_ready": False,
    "guilds": [],
    "last_error": None
}

@app.route("/")
def home():
    return "Bot läuft!"

@app.route("/status")
def status():
    return jsonify(STATUS)

def run():
    app.run(host="0.0.0.0", port=8080, use_reloader=False)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()