# utils.py
import random, string
from datetime import datetime, timedelta

def gen_key(length=12):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def days_from_now_iso(days):
    return (datetime.utcnow() + timedelta(days=int(days))).isoformat()

def is_premium_active(premium_until_iso):
    if not premium_until_iso:
        return False
    return datetime.fromisoformat(premium_until_iso) > datetime.utcnow()
