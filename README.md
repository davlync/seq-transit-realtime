# SEQ realtime recorder

Records TransLink's public GTFS-realtime TripUpdates feed for South East Queensland and keeps, for every trip and stop,
the last predicted time before the vehicle reached that stop: a close proxy for its actual arrival and departure time.

- `collect.py`: polls the feed every 30 seconds.
- `.github/workflows/collect.yml`: runs the recorder around the clock in back-to-back blocks of just under two hours and
  commits the results.
- `data/YYYY-MM-DD/HHMM.csv.gz`: one file per recording block, grouped by service date and named by the block's start
  time (Brisbane time). `1402-pilot.csv.gz` is a one-hour test recording from Saturday 31 October 2026.

Columns: `date` (service date), `trip_id`, `route_id`, `stop_id`, `seq` (stop sequence), `arr` / `dep` (predicted
arrival and departure, Unix time), `delay_arr` / `delay_dep` (seconds versus the timetable), `trip_rel` / `stop_rel`
(scheduled, added, cancelled, skipped...), `obs` (feed time of the last prediction kept), `n_obs` (number of snapshots
that included this stop). A stop time is effectively observed when `arr - obs` is a few minutes or less.

Source data: TransLink (Department of Transport and Main Roads, Queensland), GTFS-realtime,
Creative Commons Attribution 4.0.
