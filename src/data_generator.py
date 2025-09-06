import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import os

def generate_sample_data():
    fake = Faker()
    
    # Create data directory if not exists - FIXED PATH
    os.makedirs('data', exist_ok=True)
    
    # Generate 50 patients
    patients = []
    for i in range(50):
        patients.append({
            'patient_id': f"P{1000 + i}",
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'dob': fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%Y-%m-%d'),
            'phone': fake.phone_number(),
            'email': fake.email(),
            'is_returning': np.random.choice([True, False], p=[0.6, 0.4]),
            'insurance_carrier': np.random.choice(['Aetna', 'UnitedHealth', 'Cigna', 'BlueCross', 'None']),
            'member_id': f"M{np.random.randint(10000, 99999)}" if np.random.random() > 0.2 else None
        })
    
    pd.DataFrame(patients).to_csv('data/patients.csv', index=False)
    
    # Generate doctor schedules
    doctors = ['Dr. Smith', 'Dr. Johnson', 'Dr. Williams', 'Dr. Brown']
    dates = [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    schedules = []
    for doctor in doctors:
        for date in dates:
            for hour in range(9, 17):  # 9 AM to 5 PM
                if hour != 12:  # Skip lunch hour
                    schedules.append({
                        'doctor': doctor,
                        'date': date,
                        'time': f"{hour}:00",
                        'available': True
                    })
    
    pd.DataFrame(schedules).to_csv('data/doctor_schedules.csv', index=False)
    print("Sample data generated successfully in data/ folder!")

if __name__ == "__main__":
    generate_sample_data()