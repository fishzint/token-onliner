import json
import random
import logging
import requests

import threading
import websocket
from rich.console import Console

import time
import delorean
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format="\u001b[36;1m[\u001b[0m%(asctime)s\u001b[36;1m]\u001b[0m -> \u001b[36;1m%(message)s\u001b[0m",
    datefmt="%H:%M:%S",
)

class Discord(object):

    def __init__(self):
        self.tokens = []

        with open("data/spotify songs.json") as f:
            self.songs = json.loads(f.read())
        with open("data/config.json") as f:
            self.config = json.loads(f.read())
        with open("data/custom status.txt", encoding="utf-8") as f:
            self.status = [i.strip() for i in f]
        with open("data/user bios.txt", encoding="utf-8") as f:
            self.bios = [i.strip() for i in f]
        for line in open("data/tokens.txt"):
            if ":" in line.replace("\n", ""):
                token = line.replace("\n", "").split(":")[0]
            else:
                token = line.replace("\n", "")
            self.tokens.append(token)

        self.ack = json.dumps({
            "op": 1,
            "d": None
        })

        self.activities = {}
        self.vcs = []

    def nonce(self):
        date = datetime.now()
        unixts = time.mktime(date.timetuple())
        return str((int(unixts)*1000-1420070400000)*4194304)

    def random_time(self):
        return (int(delorean.Delorean(datetime.now(timezone.utc), timezone="UTC").epoch) * 1000) - random.randint(100000, 10000000)

    def random(self, data: dict):
        val_sum = sum(data.values())
        d_pct = {k: v/val_sum for k, v in data.items()}
        return next(iter(random.choices(population=list(d_pct), weights=d_pct.values(), k=1)))

    def update_bio(self, token: str, bio: any):
        r = requests.patch("https://discord.com/api/v9/users/@me", json={"bio": bio}, headers={"authorization": token})
        if r.status_code == 200 or r.status_code == 201:
            logging.info("Updated \u001b[36;1m%s\u001b[0m's bio \u001b[36;1m(\u001b[0m%s\u001b[36;1m)" % (token[:20], bio))

    def payload(self, token: str):
        type = self.random(self.config["status"])
        if type == "normal":
            activities = []
        if type == "playing":
            activities = [{
                "type": 0,
                "timestamps": {
                    "start": self.random_time()
                },
                "name": self.random(self.config["games"]),
            }]
        if type == "spotify":
            song = random.choice(self.songs)
            activities = [{
                "id": "spotify:1",
                "type": 2,
                "flags": 48,
                "name": "Spotify",
                "state": song["artists"][0]["name"],
                "details": song["name"],
                "timestamps": {
                    "start": (int(delorean.Delorean(datetime.now(timezone.utc), timezone="UTC").epoch) * 1000),
                    "end": (int(delorean.Delorean(datetime.now(timezone.utc), timezone="UTC").epoch) * 1000) + random.randint(100000, 300000)
                },
                "party": {
                    "id": "spotify:%s" % (self.nonce())
                },
                "assets": {
                    "large_image": "spotify:%s" % (song["images"][0]["url"].split("https://i.scdn.co/image/")[1])
                }
            }]
        if type == "visual_studio":
            workspace = random.choice(self.config["visual_studio"]["workspaces"])
            filename = random.choice(self.config["visual_studio"]["names"])
            activities = [{
                "type": 0,
                "name": "Visual Studio Code",
                "state": "Workspace: %s" % (workspace),
                "details": "Editing %s" % (filename),
                "application_id": "383226320970055681",
                "timestamps": {
                    "start": self.random_time()
                },
                "assets": {
                    "small_text": "Visual Studio Code",
                    "small_image": "565945770067623946",
                    "large_image": self.config["visual_studio"]["images"][filename.split(".")[1]]
                },
            }]

        logging.info("Updated \u001b[36;1m%s\u001b[0m's status \u001b[36;1m(\u001b[0m%s\u001b[36;1m)" % (token[:20], type))

        if self.config["update_status"]:
            if self.random(self.config["custom_status"]) == "yes":
                user_status = random.choice(self.status)
                activities.append({
                    "type": 4,
                    "state": user_status,
                    "name": "Custom Status",
                    "id": "custom",
                    "emoji": {
                        "id": None,
                        "name": "ð",
                        "animated": False
                    }
                })

        payload = json.dumps({
            "op": 3,
            "d": {
                "since": 0,
                "activities": activities,
                "status": random.choice(["online", "dnd", "idle"]),
                "afk": False
            }
        })

        self.activities[token] = (payload)
        return payload

    def connect(self, token: str):
        try:
            token = token.split(":")[2]
        except IndexError:
            pass

        try:
            ws = websocket.WebSocket()
            ws.connect("wss://gateway.discord.gg/?v=6&encoding=json")

            data = json.loads(ws.recv())
            heartbeat_interval = data["d"]["heartbeat_interval"]

            device = self.random({
                "Discord iOS": 25,
                "Windows": 75
            })

            ws.send(json.dumps({
                "op": 2,
                "d": {
                    "token": token,
                    "properties": {
                        "$os": device,
                        "$browser": device,
                        "$device": device
                    }
                },
                "s": None,
                "t": None
            }))

            ws.send(self.payload(token))

            if self.config["voice"]:
                if self.random(self.config["join_voice"]) == "yes":
                    channel = random.choice(self.config["vcs"])
                    ws.send(json.dumps({"op": 4,"d": {"guild_id": self.config["guild"],"channel_id": channel,"self_mute": random.choice([True, False]),"self_deaf": random.choice([True, False])}}))
                    if self.random(self.config["livestream"]) == "yes":
                        ws.send(json.dumps({"op": 18,"d": {"type": "guild","guild_id": self.config["guild"],"channel_id": channel,"preferred_region": "singapore"}}))

            if self.config["update_bio"]:
                if self.random(self.config["random_bio"]) == "yes":
                    user_bio = random.choice(self.bios)
                    self.update_bio(token, user_bio)
                else:
                    self.update_bio(token, "")

            while True:
                time.sleep(heartbeat_interval / 1000)
                try:
                    ws.send(self.ack)
                    ws.send(self.activities[token])
                except Exception:
                    discord.connect(token)
        except Exception as e:
            logging.info("Failed to connect \u001b[36;1m(\u001b[0m%s\u001b[36;1m)" % (e))
            discord.connect(token)

if __name__ == "__main__":
    discord = Discord()
    for token in discord.tokens:
        threading.Thread(target=discord.connect, args=(token,)).start()
