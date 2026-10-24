PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS fault_reports; DROP TABLE IF EXISTS bookings; DROP TABLE IF EXISTS semester_timetables;
DROP TABLE IF EXISTS equipment; DROP TABLE IF EXISTS periods; DROP TABLE IF EXISTS labs;

CREATE TABLE periods (period_no INTEGER PRIMARY KEY, start_time TEXT NOT NULL, end_time TEXT NOT NULL);

CREATE TABLE labs (
  lab_id INTEGER PRIMARY KEY, name TEXT NOT NULL, lab_type TEXT NOT NULL,
  capacity INTEGER NOT NULL CHECK (capacity > 0),            -- = number of working systems
  status TEXT NOT NULL CHECK (status IN ('available','maintenance')),
  location TEXT, software_tags TEXT);

CREATE TABLE equipment (
  equipment_id INTEGER PRIMARY KEY, lab_id INTEGER NOT NULL REFERENCES labs(lab_id),
  asset_tag TEXT, name TEXT NOT NULL, category TEXT, specs TEXT,
  status TEXT NOT NULL CHECK (status IN ('working','faulty','under_repair')), purchase_date TEXT);

CREATE TABLE semester_timetables (
  template_id INTEGER PRIMARY KEY, assigned_lab_id INTEGER REFERENCES labs(lab_id),
  batch TEXT NOT NULL, subject TEXT NOT NULL, faculty TEXT, lab_type TEXT, student_count INTEGER,
  day_of_week TEXT NOT NULL CHECK (day_of_week IN ('Mon','Tue','Wed','Thu','Fri')),
  start_period INTEGER REFERENCES periods(period_no), end_period INTEGER REFERENCES periods(period_no),
  start_time TEXT NOT NULL, end_time TEXT NOT NULL,
  semester_label TEXT, semester_start TEXT NOT NULL, semester_end TEXT NOT NULL,
  is_locked INTEGER DEFAULT 0, status TEXT, confidence TEXT, source_note TEXT);

CREATE TABLE bookings (
  booking_id INTEGER PRIMARY KEY, lab_id INTEGER NOT NULL REFERENCES labs(lab_id),
  booking_date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
  start_period INTEGER, end_period INTEGER,
  batch TEXT, subject TEXT, faculty TEXT, student_count INTEGER,
  booking_type TEXT NOT NULL CHECK (booking_type IN ('regular','semester','placement')),
  priority INTEGER NOT NULL DEFAULT 1,                       -- 1=regular, 2=semester, 3=placement
  status TEXT NOT NULL CHECK (status IN ('confirmed','pending','cancelled','completed')),
  recurrence TEXT DEFAULT 'none', semester_start TEXT, semester_end TEXT, is_locked INTEGER DEFAULT 0,
  template_id INTEGER REFERENCES semester_timetables(template_id), requested_by TEXT, created_at TEXT);

CREATE TABLE fault_reports (
  fault_id INTEGER PRIMARY KEY, equipment_id INTEGER NOT NULL REFERENCES equipment(equipment_id),
  fault_description TEXT, fault_date TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','under_repair','resolved')), resolved_date TEXT);

CREATE INDEX idx_bookings_lab_date ON bookings(lab_id, booking_date);
CREATE INDEX idx_faults_equipment ON fault_reports(equipment_id, fault_date);
