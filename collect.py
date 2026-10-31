"""Record TransLink SEQ realtime TripUpdates and keep, for every trip x stop, the last prediction made before the
vehicle reached the stop (a close proxy for the actual arrival/departure time).

Usage: python collect.py --minutes 55 --interval 30 --out data
Writes data/YYYY-MM-DD.csv.gz (one row per service date x trip x stop), merging with any file already there.
Columns: date, trip_id, route_id, stop_id, seq, arr, dep, delay_arr, delay_dep, trip_rel, stop_rel, obs, n_obs
(arr / dep are Unix seconds; obs is the feed time of the last prediction kept.)
"""
import argparse, gzip, io, os, sys, time, urllib.request
import pandas as pd
from google.transit import gtfs_realtime_pb2 as rt

URL = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/TripUpdates"
REL = {0: "scheduled", 1: "added", 2: "unscheduled", 3: "cancelled", 5: "replacement", 6: "duplicated", 7: "deleted"}
SREL = {0: "scheduled", 1: "skipped", 2: "no_data"}
GRACE = 90  # keep updating a stop until this many seconds after its predicted time


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "seq-reliability-research/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        f = rt.FeedMessage(); f.ParseFromString(r.read()); return f


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--minutes", type=float, default=55); ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--out", default="data"); ap.add_argument("--chunks", action="store_true"); a = ap.parse_args()
    os.environ.setdefault("TZ", "Australia/Brisbane"); time.tzset(); start = time.time()
    os.makedirs(a.out, exist_ok=True)
    rec = {}  # (date, trip, seq) -> row
    end = time.time() + a.minutes * 60; n = 0; fails = 0
    while time.time() < end:
        t0 = time.time()
        try:
            f = fetch(); ts = f.header.timestamp or int(t0); n += 1
            for e in f.entity:
                if not e.HasField("trip_update"):
                    continue
                tu = e.trip_update; tr = tu.trip
                for s in tu.stop_time_update:
                    arr = s.arrival.time if s.HasField("arrival") and s.arrival.time else None
                    dep = s.departure.time if s.HasField("departure") and s.departure.time else None
                    when = arr or dep
                    key = (tr.start_date, tr.trip_id, s.stop_sequence)
                    old = rec.get(key)
                    if when is not None and ts > when + GRACE and old is not None:
                        continue  # vehicle has passed: freeze the last pre-arrival prediction
                    rec[key] = {"date": tr.start_date, "trip_id": tr.trip_id, "route_id": tr.route_id, "stop_id": s.stop_id, "seq": s.stop_sequence,
                                "arr": arr, "dep": dep,
                                "delay_arr": s.arrival.delay if s.HasField("arrival") and s.arrival.HasField("delay") else None,
                                "delay_dep": s.departure.delay if s.HasField("departure") and s.departure.HasField("delay") else None,
                                "trip_rel": REL.get(tr.schedule_relationship, str(tr.schedule_relationship)),
                                "stop_rel": SREL.get(s.schedule_relationship, str(s.schedule_relationship)),
                                "obs": ts, "n_obs": (old["n_obs"] + 1) if old else 1}
            fails = 0
        except Exception as ex:
            fails += 1; print("fetch failed:", ex, file=sys.stderr, flush=True)
            if fails > 20:
                break
        if n % 10 == 0:
            print(f"{time.strftime('%H:%M:%S')} snapshots={n} records={len(rec)}", flush=True)
        time.sleep(max(1, a.interval - (time.time() - t0)))
    if not rec:
        return
    df = pd.DataFrame(rec.values())
    stamp = time.strftime("%H%M", time.localtime(start))
    for d, g in df.groupby("date"):
        if a.chunks:  # one file per run, never rewritten (keeps git history small)
            folder = os.path.join(a.out, f"{d[:4]}-{d[4:6]}-{d[6:]}"); os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{stamp}.csv.gz")
        else:
            path = os.path.join(a.out, f"{d[:4]}-{d[4:6]}-{d[6:]}.csv.gz")
            if os.path.exists(path):
                old = pd.read_csv(path, dtype={"date": str, "trip_id": str, "route_id": str, "stop_id": str})
                g = pd.concat([old, g]).sort_values("obs").drop_duplicates(["date", "trip_id", "seq"], keep="last")
        g.sort_values(["trip_id", "seq"]).to_csv(path, index=False, compression="gzip")
        print(f"wrote {path}: {len(g)} rows", flush=True)


if __name__ == "__main__":
    main()
