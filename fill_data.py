from langchain_openai import ChatOpenAI
import json
import sqlite3

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def construct_question(json_context: dict, target_variable: str, output_type: str = None, output_options: list = None):
    context_str = json.dumps(json_context, indent=2)

    prompt = f"Given the following context:\n{context_str}\n\n"

    prompt += f"Please construct a question to ask the user to obtain the value for '{target_variable}'"
    
    if output_type:
        prompt += f" that is of type '{output_type}'"
    
    if output_options:
        options_str = ', '.join(output_options)
        prompt += f" and should be one of the following options: {options_str}"
    
    prompt += "."

    response = llm.predict(prompt)

    return response.strip()

def get_patient_names():
    conn = sqlite3.connect('healthcare_triage.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM patients')
    patients = cursor.fetchall()
    
    conn.close()
    return [patient[0] for patient in patients]

def get_missing_info(patient_name):
    conn = sqlite3.connect('healthcare_triage.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT patient_id FROM patients WHERE name = ?', (patient_name,))
    patient_id = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT patient_id, priority_level, heart_rate, blood_pressure, temperature 
    FROM triage 
    WHERE patient_id = ?
    ''', (patient_id,))
    triage_data = cursor.fetchone()
    
    cursor.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,))
    patient_data = cursor.fetchone()

    context = {
        "patient": {
            "name": patient_data[1],
            "age": patient_data[2],
            "medical_history": patient_data[3]
        },
        "triage": {
            "priority_level": triage_data[1],
            "heart_rate": triage_data[2],
            "blood_pressure": triage_data[3],
            "temperature": triage_data[4]
        }
    }

    return context, patient_id

def update_missing_info(patient_id, target_variable, user_input):
    conn = sqlite3.connect('healthcare_triage.db')
    cursor = conn.cursor()
    
    if target_variable == "heart rate":
        cursor.execute('UPDATE triage SET heart_rate = ? WHERE patient_id = ?', (user_input, patient_id))
    elif target_variable == "blood_pressure":
        cursor.execute('UPDATE triage SET blood_pressure = ? WHERE patient_id = ?', (user_input, patient_id))
    elif target_variable == "temperature":
        cursor.execute('UPDATE triage SET temperature = ? WHERE patient_id = ?', (user_input, patient_id))
    
    conn.commit()
    conn.close()

patient_names = get_patient_names()
print("Patients:")
for name in patient_names:
    print(f"- {name}")

selected_patient = input("please type the exact name of the patient you want to select: ")

context, patient_id = get_missing_info(selected_patient)
if context:
    missing_variables = []
    if context["triage"]["heart_rate"] is None:
        missing_variables.append("heart rate")
    if context["triage"]["blood_pressure"] is None:
        missing_variables.append("blood pressure")
    if context["triage"]["temperature"] is None:
        missing_variables.append("temperature")

    for variable in missing_variables:
        if variable == "heart rate":
            resultType = "number"
        elif variable == "blood pressure":
            resultType = "text"
        elif variable == "temperature":
            resultType = "number"

        question = construct_question(context, variable, resultType)
        print(f"The constructed question is: {question}")

        user_input = input(f"{question}\nYour answer: ")

        update_missing_info(patient_id, variable, user_input)

    print("Database updated with the new information.")
else:
    print("No missing information found.")
