import csv
import pandas as pd
import os
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
csv_file = 'appointments.csv'

class AppointmentScheduler:
    def __init__(self, csv_file):
        self.appointments = pd.read_csv(csv_file)

    def make_appointment(self):
        appointment_data = self.collect_appointment_info()
        self.add_appointment_to_csv(appointment_data)
        print("Appointment scheduled successfully!")

    def reschedule_appointment(self):
        appointment_data = self.collect_appointment_info()
        print("Appointment rescheduled successfully!")

    def collect_appointment_info(self):
        appointment_data = {}
        print("Let's schedule an appointment.")
        for field in ['first name', 'last name', 'appointment start time',
                      'appointment end time', 'location', 'reason for visit']:
            answer = self.prompt_user(f"Please provide the {field}: ")
            appointment_data[field] = answer
        return appointment_data

    def prompt_user(self, prompt):
        response = openai.Completion.create(
            engine="davinci",
            prompt=f">> GPT-3: {prompt}",
            max_tokens=64,
        )
        return response['choices'][0]['text'].strip()

    def add_appointment_to_csv(self, appointment_data):
        with open(csv_file, 'a', newline='') as csvfile:
            fieldnames = ['first name', 'last name', 'appointment start time',
                          'appointment end time', 'location', 'reason for visit']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(appointment_data)

if __name__ == "__main__":
    scheduler = AppointmentScheduler(csv_file)
    while True:
        action = input("What would you like to do? (make appointment / reschedule / quit): ").lower()
        if action == 'make appointment':
            scheduler.make_appointment()
        elif action == 'reschedule':
            scheduler.reschedule_appointment()
        elif action == 'quit':
            print("Exiting appointment scheduler.")
            break
        else:
            print("Invalid action. Please choose 'make appointment', 'reschedule', or 'quit'.")
