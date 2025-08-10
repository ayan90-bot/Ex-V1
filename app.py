# app.py
import os
import imghdr
from flask import Flask, request, abort
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from db import init_db, add_or_update_user, set_pending, get_user, set_free_redeem_used, add_redeem_request, add_key, check_key, remove_key, set_premium, set_ban, list_all_users, get_conn
from utils import gen_key, days_from_now_iso, is_premium_active
from datetime import datetime
import sqlite3

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # required
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")  # https://yourservice.onrender.com

if not BOT_TOKEN or not ADMIN_ID:
    raise RuntimeError("BOT_TOKEN and ADMIN_ID env vars required")

bot = Bot(BOT_TOKEN)
app = Flask(__name__)

# init DB
init_db()

# Dispatcher for handling updates
dispatcher = Dispatcher(bot, None, use_context=True)

# ---- Helpers ----
def main_menu_keyboard():
    kb = [
        [InlineKeyboardButton("Redeem Request", callback_data="redeem")],
        [InlineKeyboardButton("Buy Premium", callback_data="buy")],
        [InlineKeyboardButton("Service", callback_data="service")],
        [InlineKeyboardButton("Dev", callback_data="dev")]
    ]
    return InlineKeyboardMarkup(kb)

# ---- Handlers ----
def start(update, context):
    user = update.effective_user
    add_or_update_user(user.id, user.username or "", user.first_name or "")
    update.message.reply_text(f"Hello {user.first_name or user.username}!\nWelcome to LogicX 🔥", reply_markup=main_menu_keyboard())

def button_cb(update, context):
    query = update.callback_query
    user = query.from_user
    add_or_update_user(user.id, user.username or "", user.first_name or "")
    query.answer()
    data = query.data

    if data == "redeem":
        # set pending action
        set_pending(user.id, "redeem")
        query.message.reply_text("Enter Details for redeem request. Free users: one time. Premium: unlimited while key valid.")
    elif data == "buy":
        set_pending(user.id, "buy_key")
        query.message.reply_text("Please enter your premium key to activate:")
    elif data == "service":
        query.message.reply_text("Choose service:\n1. Prime Video\n2. Spotify\n3. Crunchyroll\n4. Turbo VPN\n5. Hotspot Shield VPN")
    elif data == "dev":
        query.message.reply_text("@YourAizen")

def handle_text(update, context):
    user = update.effective_user
    text = update.message.text.strip()
    add_or_update_user(user.id, user.username or "", user.first_name or "")

    u = get_user(user.id)
    if u and u.get("banned"):
        update.message.reply_text("You are banned.")
        return

    pending = u.get("pending_action") if u else None

    # Redeem flow
    if pending == "redeem":
        # check free/premium
        if u["free_redeem_used"] == 1 and not is_premium_active(u["premium_until"]):
            update.message.reply_text("You have already used your free redeem. Buy premium for unlimited.")
            # clear pending
            set_pending(user.id, None)
            return

        # store redeem request and forward to admin
        add_redeem_request(user.id, user.username or "", text)
        bot.send_message(ADMIN_ID, f"New redeem request from @{user.username or user.id} ({user.id}):\n\n{text}")
        if u["free_redeem_used"] == 0 and not is_premium_active(u["premium_until"]):
            set_free_redeem_used(user.id)
        set_pending(user.id, None)
        update.message.reply_text("Your redeem request has been sent to admin. Thank you.")
        return

    # Buy premium flow (enter key)
    if pending == "buy_key":
        key = text
        expires_iso = check_key(key)
        if not expires_iso:
            update.message.reply_text("Invalid key.")
            set_pending(user.id, None)
            return
        # activate premium
        set_premium(user.id, expires_iso)
        # remove key so cannot be reused (optional: you may keep single-use)
        remove_key(key)
        bot.send_message(ADMIN_ID, f"User @{user.username or user.id} ({user.id}) activated premium until {expires_iso} with key {key}")
        update.message.reply_text(f"Premium activated until {expires_iso}.")
        set_pending(user.id, None)
        return

    # no pending -> normal message
    update.message.reply_text("Use the menu below.", reply_markup=main_menu_keyboard())

# ---- Admin Commands ----
def genk_cmd(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 1:
        update.message.reply_text("Usage: /genk <days>")
        return
    days = int(args[0])
    key = gen_key()
    expires_iso = days_from_now_iso(days)
    add_key(key, expires_iso)
    update.message.reply_text(f"Generated key: {key} (valid {days} days until {expires_iso})")

def broadcast_cmd(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    text = " ".join(context.args)
    if not text:
        update.message.reply_text("Usage: /broadcast <message>")
        return
    users = list_all_users()
    sent = 0
    for uid in users:
        try:
            bot.send_message(uid, text)
            sent += 1
        except Exception as e:
            print("broadcast failed", uid, e)
    update.message.reply_text(f"Broadcast sent to {sent} users.")

def ban_cmd(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if not context.args:
        update.message.reply_text("Usage: /ban <user_id>")
        return
    target = int(context.args[0])
    set_ban(target, 1)
    update.message.reply_text(f"Banned {target}")
    try:
        bot.send_message(target, "You have been banned by admin.")
    except:
        pass

def unban_cmd(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    if not context.args:
        update.message.reply_text("Usage: /unban <user_id>")
        return
    target = int(context.args[0])
    set_ban(target, 0)
    update.message.reply_text(f"Unbanned {target}")
    try:
        bot.send_message(target, "You have been unbanned by admin.")
    except:
        pass

# register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button_cb))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dispatcher.add_handler(CommandHandler("genk", genk_cmd, pass_args=True))
dispatcher.add_handler(CommandHandler("broadcast", broadcast_cmd, pass_args=True))
dispatcher.add_handler(CommandHandler("ban", ban_cmd, pass_args=True))
dispatcher.add_handler(CommandHandler("unban", unban_cmd, pass_args=True))

# webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "OK"
    else:
        abort(403)

# optional root: set webhook on start if external url provided
@app.route("/")
def index():
    return "Bot is running."

def set_hook():
    if RENDER_EXTERNAL_URL:
        url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        bot.set_webhook(url)
        print("Webhook set to", url)
    else:
        print("RENDER_EXTERNAL_URL not set; please set manually and call setWebhook.")

if __name__ == "__main__":
    set_hook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
