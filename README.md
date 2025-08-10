# LogicX Telegram Bot (Render deploy)

## Env vars required
- BOT_TOKEN = <your telegram bot token>
- ADMIN_ID = <your telegram user id (integer)>
- RENDER_EXTERNAL_URL = https://<your-render-service>.onrender.com

## How to run locally
pip install -r requirements.txt
export BOT_TOKEN=...
export ADMIN_ID=...
export RENDER_EXTERNAL_URL=http://localhost:5000  # only for webhook set
python app.py

## Deploy to Render
1. Create a new Web Service on Render (Python).
2. Connect your repo.
3. Set Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Add environment variables on Render: BOT_TOKEN, ADMIN_ID, RENDER_EXTERNAL_URL (the URL Render gives you, e.g. https://your-app.onrender.com).
6. After deploy, webhook will be set automatically (app tries to set it on start). Verify with `getWebhookInfo` or by sending /start to bot.

## Notes
- DB is local sqlite `bot.db` in app root (suitable for small bots). For production, use PostgreSQL or another DB.
- Keys generated with /genk are single-use in this code (they're removed after activation). Modify if you want multi-use.
