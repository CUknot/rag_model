import streamlit as st
import random
import time
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Streamlit App",
    page_icon="💬",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
<style>
.chat-message {
    padding: 1.5rem; 
    border-radius: 0.5rem; 
    margin-bottom: 1rem; 
    display: flex;
    flex-direction: row;
    align-items: flex-start;
}
.chat-message.user {
    background-color: #2b313e;
}
.chat-message.bot {
    background-color: #475063;
}
.chat-message .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    margin-right: 1rem;
}
.chat-message .message {
    flex: 1;
    color: #ffffff;
    font-size: 1rem;
}
.stTextInput > div > div > input {
    background-color: #2b313e;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# App title
st.title("💬 Chatbot")
st.caption("A chatbot with dummy responses")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "bot", "content": "Hello! How can I help you today? You can also check the File Manager in the sidebar."}
    ]

# Dummy responses
dummy_responses = [
    "That's interesting! Tell me more about it.",
    "I understand. Let me think about that for a moment.",
    "That's a great question! The answer depends on several factors.",
    "I appreciate your input. Here's what I think about that...",
    "Thanks for sharing that with me. Have you considered an alternative approach?",
    "I see what you mean. Let me offer a different perspective.",
    "That's a common concern. Many people have similar questions.",
    "I'm here to help! Let me know if you need more information.",
    "That's a complex topic. Let me break it down for you.",
    "I'm glad you asked about that. It's an important consideration."
]

# Function to get a dummy response
def get_dummy_response(user_input):
    # Wait to simulate thinking
    time.sleep(1)
    
    # Check for specific keywords to give more relevant responses
    if "hello" in user_input.lower() or "hi" in user_input.lower():
        return "Hello there! How can I assist you today?"
    elif "how are you" in user_input.lower():
        return "I'm just a program, but I'm functioning well! How are you doing?"
    elif "bye" in user_input.lower() or "goodbye" in user_input.lower():
        return "Goodbye! Feel free to come back if you have more questions."
    elif "thank" in user_input.lower():
        return "You're welcome! I'm happy to help."
    elif "help" in user_input.lower():
        return "I'm here to help! What do you need assistance with?"
    elif "time" in user_input.lower():
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"The current time is {current_time}."
    elif "date" in user_input.lower():
        current_date = datetime.now().strftime("%Y-%m-%d")
        return f"Today's date is {current_date}."
    elif "file" in user_input.lower() or "files" in user_input.lower():
        return "You can manage your files in the File Manager page. Check the sidebar to navigate there!"
    elif "name" in user_input.lower():
        return "My name is ChatBot. I'm a simple demonstration bot."
    else:
        # Return a random response for other inputs
        return random.choice(dummy_responses)

# Display chat messages from history
for message in st.session_state.messages:
    with st.container():
        st.markdown(f"""
        <div class="chat-message {message['role']}">
            <img class="avatar" src="{'https://api.dicebear.com/7.x/bottts/svg?seed=bot' if message['role'] == 'bot' else 'https://api.dicebear.com/7.x/personas/svg?seed=user'}" />
            <div class="message">{message['content']}</div>
        </div>
        """, unsafe_allow_html=True)

# User input area
with st.container():
    user_input = st.text_input("Your message:", key="user_input", placeholder="Type your message here...")
    
    # Handle user input
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.container():
            st.markdown(f"""
            <div class="chat-message user">
                <img class="avatar" src="https://api.dicebear.com/7.x/personas/svg?seed=user" />
                <div class="message">{user_input}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Get bot response
        with st.spinner("Thinking..."):
            response = get_dummy_response(user_input)
        
        # Add bot response to chat history
        st.session_state.messages.append({"role": "bot", "content": response})
        
        # Display bot response
        with st.container():
            st.markdown(f"""
            <div class="chat-message bot">
                <img class="avatar" src="https://api.dicebear.com/7.x/bottts/svg?seed=bot" />
                <div class="message">{response}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Clear the input box
        st.rerun()

# Add a clear button
if st.button("Clear Conversation"):
    st.session_state.messages = [
        {"role": "bot", "content": "Hello! How can I help you today? You can also check the File Manager in the sidebar."}
    ]
    st.rerun()

# Display information about the app
with st.expander("About this app"):
    st.markdown("""
    This is a simple Streamlit application with two pages:
    
    1. **Chatbot** (current page): A simple chatbot with dummy responses
    2. **File Manager**: A page to manage files (add, delete, view)
    
    Use the sidebar to navigate between pages.
    """)

# Initialize dummy files if not already in session state
if "files" not in st.session_state:
    st.session_state.files = [
        {"name": "document.txt", "type": "text", "size": "10 KB", "date": "2023-05-15"},
        {"name": "image.jpg", "type": "image", "size": "1.2 MB", "date": "2023-05-10"},
        {"name": "spreadsheet.xlsx", "type": "excel", "size": "256 KB", "date": "2023-05-01"}
    ]
