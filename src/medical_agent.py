import pandas as pd
import re
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from dotenv import load_dotenv

load_dotenv()

class MedicalSchedulingAgent:
    def __init__(self):
        try:
            self.patient_db = pd.read_csv('data/patients.csv')
            self.schedule_db = pd.read_csv('data/doctor_schedules.csv')
            # Load existing appointments if file exists
            try:
                self.all_appointments = pd.read_excel('data/all_appointments.xlsx')
            except:
                self.all_appointments = pd.DataFrame()
        except:
            self.patient_db = pd.DataFrame(columns=['first_name', 'last_name', 'dob', 'is_returning'])
            self.schedule_db = pd.DataFrame(columns=['doctor', 'date', 'time', 'available'])
            self.all_appointments = pd.DataFrame()
        
        self.current_step = "get_name"
        self.patient_info = {}
        self.appointment_info = {}
        self.insurance_info = {}
        self.available_slots = None
    
    def process_message(self, user_input: str):
        print(f"Processing: {user_input}, Step: {self.current_step}")
        
        # Check for cancellation at any step
        if user_input.lower() in ['cancel', 'exit', 'quit', 'stop', 'restart']:
            return self._handle_cancellation()
        
        if self.current_step == "get_name":
            return self._handle_get_name(user_input)
        
        elif self.current_step == "get_dob":
            return self._handle_get_dob(user_input)
        
        elif self.current_step == "show_calendar":
            # Return both the message and trigger calendar UI
            return {"message": "Please select an available time slot from the calendar.", "show_calendar": True}
        
        elif self.current_step == "get_insurance":
            return self._handle_get_insurance(user_input)
        
        elif self.current_step == "get_email":
            return self._handle_get_email(user_input)
        
        elif self.current_step == "confirm":
            return self._handle_confirm()
        
        else:
            return "I'm not sure what to do next. Please start over."
    
    def _handle_cancellation(self):
        """Handle appointment cancellation"""
        self._reset_session()
        return "❌ Appointment cancelled. How can I help you today? Type your name to start a new booking."
    
    def _reset_session(self):
        """Reset the session to initial state"""
        self.current_step = "get_name"
        self.patient_info = {}
        self.appointment_info = {}
        self.insurance_info = {}
        self.available_slots = None
    
    def _handle_get_name(self, user_input: str):
        if user_input.strip():
            self.patient_info['name'] = user_input.strip()
            self.current_step = "get_dob"
            return f"Nice to meet you, {self.patient_info['name']}! What is your date of birth? (MM/DD/YYYY)\n\nYou can type 'cancel' at any time to stop the booking process."
        else:
            return "Please provide your full name. Type 'cancel' to stop."
    
    def _handle_get_dob(self, user_input: str):
        # Validate DOB format (MM/DD/YYYY or MM-DD-YYYY)
        dob_pattern = r'^(0[1-9]|1[0-2])[/-](0[1-9]|[12][0-9]|3[01])[/-]\d{4}$'
        
        if re.match(dob_pattern, user_input.strip()):
            # Convert to standard format MM/DD/YYYY
            dob = user_input.strip().replace('-', '/')
            self.patient_info['dob'] = dob
            
            # Check if patient exists and determine patient type
            name_parts = self.patient_info['name'].split()
            if len(name_parts) >= 2:
                first_name, last_name = name_parts[0], name_parts[1]
                
                # Check if patient exists with same name AND dob
                found_patient = self.patient_db[
                    (self.patient_db['first_name'].str.contains(first_name, case=False)) &
                    (self.patient_db['last_name'].str.contains(last_name, case=False)) &
                    (self.patient_db['dob'] == dob)
                ]
                
                if len(found_patient) > 0:
                    patient_type = "returning"
                    self.patient_info['patient_type'] = patient_type
                    response = f"Welcome back {self.patient_info['name']}! I found you in our system as a returning patient."
                else:
                    patient_type = "new"
                    self.patient_info['patient_type'] = patient_type
                    response = f"Nice to meet you {self.patient_info['name']}! I'll set you up as a new patient."
            else:
                patient_type = "new"
                self.patient_info['patient_type'] = patient_type
                response = f"Nice to meet you {self.patient_info['name']}! I'll set you up as a new patient."
            
            # Get available slots with smart scheduling
            try:
                self.available_slots = self._get_available_slots_with_duration()
            except Exception as e:
                print(f"Error getting available slots: {e}")
                self.available_slots = pd.DataFrame()
            
            if len(self.available_slots) > 0:
                self.current_step = "show_calendar"
                # Return both message and calendar trigger
                return {"message": response + " Please select an available time slot from the calendar.", "show_calendar": True}
            else:
                self._reset_session()
                return response + " Unfortunately, there are no available slots at the moment. Please try again later."
        else:
            return "Please provide your date of birth in MM/DD/YYYY format (e.g., 01/15/1990). Type 'cancel' to stop the booking process."
    
    def _get_available_slots_with_duration(self):
        """Get available slots considering appointment duration"""
        try:
            available_slots = self.schedule_db[self.schedule_db['available'] == True].copy()
            return available_slots
        except Exception as e:
            print(f"Error in smart scheduling: {e}")
            return self.schedule_db[self.schedule_db['available'] == True]
    
    def handle_slot_selection(self, selected_slot_info):
        try:
            doctor, date, time = selected_slot_info.split('|')
            
            # Determine appointment duration based on patient type
            duration = 60 if self.patient_info.get('patient_type') == 'new' else 30
            
            self.appointment_info = {
                'doctor': doctor,
                'date': date,
                'time': time,
                'duration': duration
            }
            
            # Mark slot as booked
            self._mark_slots_as_booked(doctor, date, time, duration)
            
            self.current_step = "get_insurance"
            duration_msg = "60 minutes" if duration == 60 else "30 minutes"
            return f"As a {self.patient_info.get('patient_type')} patient, your appointment will be {duration_msg}. Now let's collect your insurance information. Please provide:\n1. Insurance Carrier (e.g., Aetna, BlueCross)\n2. Member ID\n3. Group Number (if available)\n\nType 'cancel' to stop the booking process."
        except:
            return "Invalid slot selection. Please try again."
    
    def _mark_slots_as_booked(self, doctor, date, time, duration):
        """Mark time slots as booked based on appointment duration"""
        try:
            # For 60min appointments, we need to block the next 30min slot too
            if duration == 60:
                # Convert time to datetime for calculation
                slot_time = datetime.strptime(time, '%H:%M')
                # Calculate next time slot (30 minutes later)
                next_slot_time = (slot_time + timedelta(minutes=30)).strftime('%H:%M')
                
                # Mark both current and next slot as unavailable
                slots_to_mark = [
                    (doctor, date, time),
                    (doctor, date, next_slot_time)
                ]
            else:
                # For 30min appointments, just mark the selected slot
                slots_to_mark = [(doctor, date, time)]
            
            # Update schedule database
            for doc, dt, tm in slots_to_mark:
                mask = (
                    (self.schedule_db['doctor'] == doc) &
                    (self.schedule_db['date'] == dt) &
                    (self.schedule_db['time'] == tm)
                )
                self.schedule_db.loc[mask, 'available'] = False
            
            # Save updated schedule
            self.schedule_db.to_csv('data/doctor_schedules.csv', index=False)
            print(f"✅ Marked {len(slots_to_mark)} slot(s) as booked for {duration}min appointment")
            
        except Exception as e:
            print(f"❌ Error marking slots as booked: {e}")
    
    def _handle_get_insurance(self, user_input: str):
        user_input_lower = user_input.lower()
        
        # Extract insurance information using patterns
        insurance_carriers = ['aetna', 'bluecross', 'blue cross', 'united', 'cigna']
        for carrier in insurance_carriers:
            if carrier in user_input_lower:
                self.insurance_info['carrier'] = carrier.title().replace(' ', '')
                break
        
        # Extract member ID (pattern like M12345, ID: 12345, etc.)
        member_id_pattern = r'(?:member\s*id|id|member)\s*[:#]?\s*([A-Z0-9-]+)'
        member_match = re.search(member_id_pattern, user_input, re.IGNORECASE)
        if member_match:
            self.insurance_info['member_id'] = member_match.group(1)
        
        # Extract group number
        group_pattern = r'(?:group\s*number|group)\s*[:#]?\s*([A-Z0-9-]+)'
        group_match = re.search(group_pattern, user_input, re.IGNORECASE)
        if group_match:
            self.insurance_info['group_number'] = group_match.group(1)
        
        # Check if we have all required info
        if 'carrier' in self.insurance_info and 'member_id' in self.insurance_info:
            self.current_step = "get_email"
            summary = f"Insurance information received:\n- Carrier: {self.insurance_info.get('carrier')}\n- Member ID: {self.insurance_info.get('member_id')}"
            if 'group_number' in self.insurance_info:
                summary += f"\n- Group Number: {self.insurance_info.get('group_number')}"
            
            # Add duration information
            duration = self.appointment_info.get('duration', 30)
            duration_msg = "60 minutes (new patient)" if duration == 60 else "30 minutes (returning patient)"
            summary += f"\n\nAppointment Duration: {duration_msg}"
            summary += "\n\nWhat is your email address for confirmation and patient forms? Type 'cancel' to stop."
            
            return summary
        else:
            # Ask for missing information
            missing = []
            if 'carrier' not in self.insurance_info:
                missing.append("insurance carrier")
            if 'member_id' not in self.insurance_info:
                missing.append("member ID")
            
            return f"I still need your {', '.join(missing)}. Please provide the missing information. Type 'cancel' to stop."
    
    def _handle_get_email(self, user_input: str):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, user_input)
        
        if email_match:
            self.patient_info['email'] = email_match.group(0)
            self.current_step = "confirm"
            return self._handle_confirm()
        else:
            return "Please provide a valid email address. Type 'cancel' to stop the booking process."
    
    def _handle_confirm(self):
        # Generate confirmation message with duration info
        duration = self.appointment_info.get('duration', 30)
        duration_msg = "60 minutes (new patient)" if duration == 60 else "30 minutes (returning patient)"
        
        confirmation_msg = f"""
        ✅ Appointment Confirmed!
        
        Patient: {self.patient_info.get('name', 'N/A')} ({self.patient_info.get('patient_type', 'new')})
        Email: {self.patient_info.get('email', 'N/A')}
        Doctor: {self.appointment_info.get('doctor', 'N/A')}
        Date: {self.appointment_info.get('date', 'N/A')}
        Time: {self.appointment_info.get('time', 'N/A')}
        Duration: {duration_msg}
        
        Insurance Information:
        - Carrier: {self.insurance_info.get('carrier', 'Not provided')}
        - Member ID: {self.insurance_info.get('member_id', 'Not provided')}
        - Group Number: {self.insurance_info.get('group_number', 'Not provided')}
        """
        
        # Export to Excel and send email
        excel_exported = self._export_to_excel()
        email_sent = self._send_confirmation_email()
        
        # Add new patient to database if they are new
        if self.patient_info.get('patient_type') == 'new':
            self._add_new_patient_to_db()
        
        if email_sent:
            confirmation_msg += "\n\n📧 Confirmation email with patient intake form has been sent to your email address!"
        elif excel_exported:
            confirmation_msg += "\n\n✅ Appointment saved. Email could not be sent."
        else:
            confirmation_msg += "\n\n⚠️ There was an issue saving your appointment."
        
        # Reset for next conversation but keep the confirmation message
        final_response = confirmation_msg + "\n\n💬 How can I help you today? Type your name to start a new booking."
        self._reset_session()
        
        return final_response
    
    def _add_new_patient_to_db(self):
        """Add new patient to the database so they become returning next time"""
        try:
            name_parts = self.patient_info['name'].split()
            if len(name_parts) >= 2:
                first_name, last_name = name_parts[0], name_parts[1]
                
                # Create new patient record
                new_patient = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'dob': self.patient_info['dob'],
                    'email': self.patient_info.get('email', ''),
                    'phone': '',  # You can collect this later
                    'is_returning': True,  # They'll be returning next time
                    'insurance_carrier': self.insurance_info.get('carrier', ''),
                    'member_id': self.insurance_info.get('member_id', ''),
                    'group_number': self.insurance_info.get('group_number', '')
                }
                
                # Convert to DataFrame and append
                new_df = pd.DataFrame([new_patient])
                
                # Reload the current patient database to ensure we have latest data
                try:
                    current_db = pd.read_csv('data/patients.csv')
                except:
                    current_db = pd.DataFrame(columns=['first_name', 'last_name', 'dob', 'email', 'phone', 'is_returning', 'insurance_carrier', 'member_id', 'group_number'])
                
                # Append new patient and save
                updated_db = pd.concat([current_db, new_df], ignore_index=True)
                updated_db.to_csv('data/patients.csv', index=False)
                
                # Update the in-memory database
                self.patient_db = updated_db
                
                print(f"✅ Added new patient to database: {self.patient_info['name']}")
                
        except Exception as e:
            print(f"❌ Error adding patient to database: {e}")
    
    def _export_to_excel(self):
        """Export appointment to Excel master file"""
        try:
            # Create new appointment record
            new_appointment = {
                'Patient Name': self.patient_info.get('name'),
                'Patient Type': self.patient_info.get('patient_type'),
                'Patient Email': self.patient_info.get('email'),
                'Date of Birth': self.patient_info.get('dob'),
                'Doctor': self.appointment_info.get('doctor'),
                'Appointment Date': self.appointment_info.get('date'),
                'Appointment Time': self.appointment_info.get('time'),
                'Duration (min)': self.appointment_info.get('duration'),
                'Insurance Carrier': self.insurance_info.get('carrier'),
                'Member ID': self.insurance_info.get('member_id'),
                'Group Number': self.insurance_info.get('group_number'),
                'Status': 'Confirmed',
                'Booking Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Append to existing appointments or create new DataFrame
            if self.all_appointments.empty:
                self.all_appointments = pd.DataFrame([new_appointment])
            else:
                self.all_appointments = pd.concat([self.all_appointments, pd.DataFrame([new_appointment])], ignore_index=True)
            
            # Save to Excel
            self.all_appointments.to_excel('data/all_appointments.xlsx', index=False)
            print("✅ Excel export completed")
            return True
            
        except Exception as e:
            print(f"❌ Excel export failed: {e}")
            return False
    
    def _send_confirmation_email(self):
        """Send confirmation email with beautiful HTML template"""
        try:
            email_user = os.getenv("EMAIL_USER")
            email_password = os.getenv("EMAIL_PASSWORD")
            to_email = self.patient_info.get('email')
            
            if not email_user or not email_password:
                print("Email credentials not configured")
                return False
            
            if not to_email:
                print("No recipient email address")
                return False
            
            # Check if PDF form exists
            pdf_path = 'data/patient_intake_form.pdf'
            pdf_exists = pdf_path and os.path.exists(pdf_path)
            
            # Create email message with HTML content
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Medical Clinic <{email_user}>"
            msg['To'] = to_email
            msg['Subject'] = "✅ Your Appointment Confirmation - Medical Clinic"
            
            # Beautiful HTML email template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: 'Arial', sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 10px 10px 0 0;
                    }}
                    .content {{
                        background: white;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .appointment-details {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                        border-left: 4px solid #667eea;
                    }}
                    .detail-item {{
                        margin: 10px 0;
                        display: flex;
                        justify-content: space-between;
                    }}
                    .detail-label {{
                        font-weight: bold;
                        color: #555;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 15px 30px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        border-radius: 25px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        color: #666;
                        font-size: 12px;
                    }}
                    .highlight {{
                        background: #fff3cd;
                        padding: 10px;
                        border-radius: 5px;
                        border-left: 4px solid #ffc107;
                        margin: 15px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏥 Medical Clinic</h1>
                    <p>Your Health is Our Priority</p>
                </div>
                
                <div class="content">
                    <h2>Appointment Confirmed! ✅</h2>
                    <p>Dear <strong>{self.patient_info.get('name')}</strong>,</p>
                    <p>Your appointment has been successfully scheduled. We're looking forward to seeing you!</p>
                    
                    <div class="appointment-details">
                        <h3>📅 Appointment Details</h3>
                        <div class="detail-item">
                            <span class="detail-label">Doctor:</span>
                            <span>👨‍⚕️ {self.appointment_info.get('doctor')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Date:</span>
                            <span>📅 {self.appointment_info.get('date')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Time:</span>
                            <span>⏰ {self.appointment_info.get('time')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Duration:</span>
                            <span>⏱️ {self.appointment_info.get('duration')} minutes ({self.patient_info.get('patient_type')} patient)</span>
                        </div>
                    </div>
                    
                    <div class="appointment-details">
                        <h3>📋 Insurance Information</h3>
                        <div class="detail-item">
                            <span class="detail-label">Carrier:</span>
                            <span>🏢 {self.insurance_info.get('carrier', 'Not provided')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Member ID:</span>
                            <span>🔖 {self.insurance_info.get('member_id', 'Not provided')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Group Number:</span>
                            <span>👥 {self.insurance_info.get('group_number', 'Not provided')}</span>
                        </div>
                    </div>
                    
                    <div class="highlight">
                        <h4>📎 Important Documents Attached</h4>
                        <p>We've attached the patient intake form for you to complete before your visit.</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <p>Please arrive <strong>15 minutes early</strong> for your appointment.</p>
                        <p>Bring your insurance card and photo ID.</p>
                    </div>
                    
                    <div class="footer">
                        <p>📍 123 Medical Center Drive, Healthcare City</p>
                        <p>📞 (555) 123-4567 | ✉️ info@medicalclinic.com</p>
                        <p>© 2024 Medical Clinic. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version for email clients that don't support HTML
            text_content = f"""
            APPOINTMENT CONFIRMATION - MEDICAL CLINIC
            
            Dear {self.patient_info.get('name')},
            
            Your appointment has been confirmed:
            
            DOCTOR: {self.appointment_info.get('doctor')}
            DATE: {self.appointment_info.get('date')}
            TIME: {self.appointment_info.get('time')}
            DURATION: {self.appointment_info.get('duration')} minutes ({self.patient_info.get('patient_type')} patient)
            
            INSURANCE INFORMATION:
            - Carrier: {self.insurance_info.get('carrier', 'Not provided')}
            - Member ID: {self.insurance_info.get('member_id', 'Not provided')}
            - Group Number: {self.insurance_info.get('group_number', 'Not provided')}
            
            Please arrive 15 minutes early for your appointment.
            Bring your insurance card and photo ID.
            
            We've attached the patient intake form for you to complete.
            
            Contact Information:
            📍 123 Medical Center Drive, Healthcare City
            📞 (555) 123-4567
            ✉️ info@medicalclinic.com
            """
            
            # Attach both HTML and plain text versions
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Attach PDF file if it exists
            if pdf_exists:
                try:
                    with open(pdf_path, 'rb') as f:
                        attach = MIMEApplication(f.read(), _subtype='pdf')
                        attach.add_header('Content-Disposition', 'attachment', 
                                        filename='Patient_Intake_Form.pdf')
                        msg.attach(attach)
                    print(f"✅ Attachment added: {pdf_path}")
                except Exception as e:
                    print(f"❌ Failed to attach file: {e}")
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(email_user, email_password)
            server.sendmail(email_user, to_email, msg.as_string())
            server.quit()
            
            print(f"✅ Beautiful email sent to: {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
            return False
    
    def get_available_slots_for_ui(self):
        """Get available slots for UI display"""
        try:
            if self.available_slots is None or len(self.available_slots) == 0:
                # Return sample slots for demo
                sample_slots = [
                    {'doctor': 'Dr. Smith', 'date': '2024-01-15', 'time': '10:00', 'display': 'Dr. Smith - 2024-01-15 10:00'},
                    {'doctor': 'Dr. Smith', 'date': '2024-01-15', 'time': '11:00', 'display': 'Dr. Smith - 2024-01-15 11:00'},
                    {'doctor': 'Dr. Johnson', 'date': '2024-01-16', 'time': '14:00', 'display': 'Dr. Johnson - 2024-01-16 14:00'},
                ]
                
                # Add duration information to display
                duration = " (60min)" if self.patient_info.get('patient_type') == 'new' else " (30min)"
                for slot in sample_slots:
                    slot['display'] += duration
                
                return sample_slots
            
            slots = []
            for _, slot in self.available_slots.iterrows():
                display_text = f"{slot['doctor']} - {slot['date']} {slot['time']}"
                
                # Add duration hint
                if self.patient_info.get('patient_type') == 'new':
                    display_text += " (60min appointment)"
                else:
                    display_text += " (30min appointment)"
                
                slots.append({
                    'doctor': slot['doctor'],
                    'date': slot['date'],
                    'time': slot['time'],
                    'display': display_text
                })
            
            return slots
        except:
            # Return sample data if anything fails
            sample_slots = [
                {'doctor': 'Dr. Smith', 'date': '2024-01-15', 'time': '10:00', 'display': 'Dr. Smith - 2024-01-15 10:00 (60min)'},
                {'doctor': 'Dr. Smith', 'date': '2024-01-15', 'time': '11:00', 'display': 'Dr. Smith - 2024-01-15 11:00 (60min)'},
                {'doctor': 'Dr. Johnson', 'date': '2024-01-16', 'time': '14:00', 'display': 'Dr. Johnson - 2024-01-16 14:00 (60min)'},
            ]
            return sample_slots