import streamlit as st
from medical_agent import MedicalSchedulingAgent

# Set page config must be the first command and only once
st.set_page_config(page_title="Medical Scheduling AI", page_icon="🏥", layout="wide")

def main():
    st.title("🏥 Medical Appointment Scheduling AI Agent")
    st.write("Automated patient booking system with smart scheduling")
    
    # Initialize agent and session state
    if 'agent' not in st.session_state:
        st.session_state.agent = MedicalSchedulingAgent()
        st.session_state.conversation = []
        st.session_state.show_calendar = False
        st.session_state.selected_slot = None
        # Add initial greeting ONLY ONCE
        st.session_state.conversation.append(("agent", "Hello! Welcome to our medical clinic. I'm here to help you schedule an appointment. What is your full name?\n\nYou can type 'cancel' at any time to stop the booking process."))
    
    # Display conversation
    for speaker, message in st.session_state.conversation:
        with st.chat_message("assistant" if speaker == "agent" else "user"):
            st.write(message)
    
    # Show calendar UI when needed - NOW AT THE SAME TIME AS CHAT
    if st.session_state.show_calendar:
        st.subheader("📅 Available Time Slots")
        
        available_slots = st.session_state.agent.get_available_slots_for_ui()
        
        if not available_slots:
            st.warning("No available slots found.")
            st.session_state.show_calendar = False
            st.session_state.conversation.append(("agent", "Sorry, no slots available. Please try again later."))
            st.rerun()
        
        # Group slots by doctor
        doctors = list(set(slot['doctor'] for slot in available_slots))
        
        for doctor in doctors:
            with st.expander(f"👨‍⚕️ {doctor}", expanded=True):
                doctor_slots = [s for s in available_slots if s['doctor'] == doctor]
                
                # Group by date
                dates = list(set(slot['date'] for slot in doctor_slots))
                
                for date in sorted(dates):
                    st.write(f"**{date}**")
                    date_slots = [s for s in doctor_slots if s['date'] == date]
                    
                    # Create buttons for each time slot
                    cols = st.columns(3)
                    for i, slot in enumerate(sorted(date_slots, key=lambda x: x['time'])):
                        with cols[i % 3]:
                            if st.button(
                                f"⏰ {slot['time']}",
                                key=f"slot_{doctor}_{date}_{slot['time']}",
                                use_container_width=True
                            ):
                                st.session_state.selected_slot = f"{slot['doctor']}|{slot['date']}|{slot['time']}"
                                st.session_state.show_calendar = False
                                
                                # Process the selected slot
                                response = st.session_state.agent.handle_slot_selection(st.session_state.selected_slot)
                                st.session_state.conversation.append(("agent", response))
                                st.rerun()
        
        # Cancel button
        if st.button("❌ Cancel Booking", use_container_width=True, type="secondary"):
            response = st.session_state.agent.process_message("cancel")
            st.session_state.conversation.append(("agent", response))
            st.session_state.show_calendar = False
            st.rerun()
    
    # User input (always show, but calendar appears simultaneously)
    if prompt := st.chat_input("Type your response here... (type 'cancel' to stop)"):
        # Add user message
        st.session_state.conversation.append(("user", prompt))
        
        # Get agent response
        with st.spinner("Processing..."):
            response = st.session_state.agent.process_message(prompt)
            
            if isinstance(response, dict) and response.get("show_calendar"):
                st.session_state.show_calendar = True
                st.session_state.conversation.append(("agent", response["message"]))
            else:
                st.session_state.conversation.append(("agent", response))
        
        st.rerun()

if __name__ == "__main__":
    main()