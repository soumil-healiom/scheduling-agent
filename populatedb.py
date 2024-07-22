import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('healthcare_triage.db')
cursor = conn.cursor()

# Drop tables if they exist
cursor.execute('DROP TABLE IF EXISTS patients')
cursor.execute('DROP TABLE IF EXISTS symptoms')
cursor.execute('DROP TABLE IF EXISTS triage')

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    medical_history TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS symptoms (
    symptom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    symptom TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS triage (
    triage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    priority_level TEXT NOT NULL,
    heart_rate INTEGER,
    blood_pressure TEXT,
    temperature REAL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
)
''')

# Insert dummy data into patients table
cursor.execute('''
INSERT INTO patients (name, age, medical_history) VALUES
('John Doe', 50, 'hypertension'),
('Jane Smith', 45, 'diabetes'),
('Alice Johnson', 30, 'none'),
('Bob Brown', 60, 'heart disease, asthma')
''')

# Insert dummy data into symptoms table with missing information
cursor.execute('''
INSERT INTO symptoms (patient_id, symptom) VALUES
(1, 'chest pain'),
(1, 'shortness of breath'),
(2, 'dizziness'),
(3, 'headache')
''')

# Insert dummy data into triage table with missing information
cursor.execute('''
INSERT INTO triage (patient_id, priority_level, heart_rate, blood_pressure, temperature) VALUES
(1, 'high', 110, '150/90', 98.6),
(2, 'medium', 100, '140/85', NULL),  -- Missing temperature
(3, 'low', 70, NULL, 98.4),          -- Missing blood pressure
(4, 'high', NULL, '160/100', 99.1)   -- Missing heart rate
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database populated with dummy data successfully.")
