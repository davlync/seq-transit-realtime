"""Decide what this run should do: record the current (or next, if it opens within 100 min) busy-period window.

Windows, Brisbane time: weekdays 06:00-09:00 and 15:00-19:00; weekends 11:00-15:00. Recording stops for good at END.
Writes wait=<seconds> minutes=<minutes> stop=<0|1> to $GITHUB_OUTPUT (or prints them).
"""
import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Brisbane")
END = datetime(2026, 11, 15, 20, 0, tzinfo=TZ)
WEEKDAY = [(time(6), time(9)), (time(15), time(19))]
WEEKEND = [(time(11), time(15))]
LEAD = timedelta(minutes=100)


def windows(day):
    for a, b in (WEEKDAY if day.weekday() < 5 else WEEKEND):
        yield datetime.combine(day, a, TZ), datetime.combine(day, b, TZ)


now = datetime.now(TZ)
wait = minutes = 0
if now < END:
    for d in (now.date(), now.date() + timedelta(days=1)):
        for a, b in windows(d):
            b = min(b, END)
            if a - LEAD <= now < b - timedelta(minutes=5):
                wait = max(0, (a - now).total_seconds()); minutes = (b - max(now, a)).total_seconds() / 60 - 1
                break
        if minutes:
            break
out = f"wait={int(wait)}\nminutes={minutes:.1f}\nstop={int(now >= END)}\n"
print(now.isoformat(), out.replace("\n", " "))
if os.environ.get("GITHUB_OUTPUT"):
    open(os.environ["GITHUB_OUTPUT"], "a").write(out)
