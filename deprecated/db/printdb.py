import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('healthcare_triage.db')
cursor = conn.cursor()

# Fetch and print data from patients table
print("Patients:")
cursor.execute('SELECT * FROM patients')
patients = cursor.fetchall()
for patient in patients:
    print(f"ID: {patient[0]}, Name: {patient[1]}, Age: {patient[2]}, Medical History: {patient[3]}")

print("\nSymptoms:")
# Fetch and print data from symptoms table
cursor.execute('SELECT * FROM symptoms')
symptoms = cursor.fetchall()
for symptom in symptoms:
    print(f"Symptom ID: {symptom[0]}, Patient ID: {symptom[1]}, Symptom: {symptom[2]}")

print("\nTriage:")
# Fetch and print data from triage table
cursor.execute('SELECT * FROM triage')
triage = cursor.fetchall()
for triage_record in triage:
    print(f"Triage ID: {triage_record[0]}, Patient ID: {triage_record[1]}, Priority Level: {triage_record[2]}, "
          f"Heart Rate: {triage_record[3]}, Blood Pressure: {triage_record[4]}, Temperature: {triage_record[5]}")

# Close the connection
conn.close()
