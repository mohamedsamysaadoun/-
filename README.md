# رَوْنَق Dashboard

Web dashboard for the Rawnaq Quran Reels Bot.

## Requirements

- Python 3.10+
- Bot source code at `/home/rawnaq_bot_extracted/`
- `ffmpeg` installed (required by the bot for video generation)

## Setup

```bash
# Install Python dependencies
pip3 install -r requirements_dashboard.txt

# (Optional) install bot dependencies if not already done
pip3 install -r /home/rawnaq_bot_extracted/requirements.txt
```

## Run

```bash
bash run_dashboard.sh
# OR
python3 dashboard_server.py
```

Dashboard will be available at **http://localhost:3002**

## Structure

```
/home/-/
├── dashboard_server.py       # FastAPI backend (port 3002)
├── static/
│   └── index.html            # Single-page Arabic RTL dashboard
├── requirements_dashboard.txt
├── run_dashboard.sh
└── README.md
```

## Features

| Tab | Description |
|-----|-------------|
| 🏠 لوحة التحكم | Bot status, stats, start/stop/restart controls |
| 🎬 إنشاء ريلز | Full reel generation form with theme/sound/font selection |
| 🤖 محادثة ذكية | AI chat interface that can trigger reel generation |
| 📋 السجلات | Live log viewer with color-coded output |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | Bot status + stats |
| POST | `/api/bot/action` | start / stop / restart |
| GET | `/api/logs` | Last N log lines |
| GET | `/api/surahs` | All 114 surahs |
| GET | `/api/reciters` | Reciter list with groups |
| GET | `/api/fonts` | Available fonts |
| GET | `/api/sounds` | Nature sounds |
| POST | `/api/generate` | Generate a reel (async, up to 5 min) |
| POST | `/api/chat` | AI chat with reel intent detection |
| GET | `/api/video/{filename}` | Serve generated video |
| GET | `/output/{filename}` | Direct output file access |
