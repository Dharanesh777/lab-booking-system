"""Creates lab_booking.db from schema.sql + CSVs.  Run: python seed_db.py"""
import sqlite3, csv
import os
if os.path.exists("lab_booking.db"): os.remove("lab_booking.db")
con = sqlite3.connect("lab_booking.db")
con.executescript(open("schema.sql").read())
for tbl in ["periods","labs","equipment","semester_timetables","bookings","fault_reports"]:
    rows = list(csv.DictReader(open(f"{tbl}.csv")))
    cols = list(rows[0].keys())
    con.executemany(f"INSERT INTO {tbl} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                    [[(v if v != "" else None) for v in r.values()] for r in rows])
    print(tbl, len(rows))
con.commit()
# sanity check: overlapping confirmed/completed bookings (should be 0)
bad = con.execute("""SELECT COUNT(*) FROM bookings a JOIN bookings b
  ON a.lab_id=b.lab_id AND a.booking_date=b.booking_date AND a.booking_id<b.booking_id
  AND a.start_time<b.end_time AND b.start_time<a.end_time
  WHERE a.status IN ('confirmed','completed') AND b.status IN ('confirmed','completed')""").fetchone()[0]
print("overlapping confirmed bookings:", bad)
