# 🏥 AI-Powered Medical Appointment Scheduling System

An **AI-powered medical appointment scheduling system** designed to automate patient booking, reduce no-shows, and streamline clinic operations.  
Built with **Streamlit**, **LangGraph**, and **Google Gemini AI**, the system is modular, scalable, and ready for healthcare deployment.

---

## 🚀 Features

- **Patient Management**
  - Detects new vs. returning patients
  - Demographics & insurance data capture
  - Automated patient database updates

- **Smart Scheduling**
  - 60-minute slots for new patients
  - 30-minute slots for returning patients
  - Real-time availability checking
  - Conflict prevention & resolution

- **Communication System**
  - Email confirmations with PDF attachments
  - Automated reminders (framework ready)
  - SMS support (Twilio-ready)

- **Data Management**
  - CSV patient database
  - Excel-based reporting
  - Appointment history tracking
  - Admin dashboard-ready structure

---

## 🏗️ System Architecture

<img width="725" height="359" alt="image" src="https://github.com/user-attachments/assets/c73292df-ee38-4167-9dc3-1a1708ddf454" />


---

## ⚙️ Technology Stack

- **Frontend:** Streamlit  
- **AI Framework:** LangGraph + LangChain  
- **LLM:** Google Gemini  
- **Data Storage:** Pandas + CSV/Excel  
- **Email:** SMTP with SSL/TLS  
- **Containerization:** Docker  

---

## 📂 Project Structure

<img width="538" height="410" alt="image" src="https://github.com/user-attachments/assets/e5121cfe-d7ea-47b2-bc1e-7c508f023d15" />

---

## 🐳 Deployment

### Run with Docker
```bash
# Build the image
docker build -t medical-scheduling-agent .

# Run the container
docker run -p 8501:8501 medical-scheduling-agent
# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run src/app.py


