import streamlit as st
import pandas as pd
from datetime import datetime
import random

# Set page configuration
st.set_page_config(
    page_title="File Manager",
    page_icon="📁",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.file-card {
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #ddd;
    margin-bottom: 1rem;
}
.file-icon {
    font-size: 2rem;
    margin-right: 1rem;
}
.file-actions {
    display: flex;
    justify-content: flex-end;
}
.stButton button {
    margin-left: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# Page title
st.title("📁 File Manager")
st.caption("Add, delete, and view files")

# Initialize dummy files if not already in session state
if "files" not in st.session_state:
    st.session_state.files = [
        {"name": "document.txt", "type": "text", "size": "10 KB", "date": "2023-05-15"},
        {"name": "image.jpg", "type": "image", "size": "1.2 MB", "date": "2023-05-10"},
        {"name": "spreadsheet.xlsx", "type": "excel", "size": "256 KB", "date": "2023-05-01"}
    ]

# Function to get file icon based on type
def get_file_icon(file_type):
    icons = {
        "text": "📄",
        "image": "🖼️",
        "pdf": "📕",
        "excel": "📊",
        "word": "📝",
        "audio": "🎵",
        "video": "🎬",
        "archive": "🗄️",
        "code": "💻",
        "other": "📎"
    }
    return icons.get(file_type.lower(), icons["other"])

# Function to get random file size
def get_random_size():
    sizes = ["10 KB", "256 KB", "512 KB", "1.2 MB", "2.5 MB", "4.7 MB", "10 MB"]
    return random.choice(sizes)

# Add new file section
st.header("Add New File")
with st.form("add_file_form"):
    col1, col2 = st.columns(2)
    with col1:
        file_name = st.text_input("File Name", placeholder="Enter file name with extension (e.g., document.txt)")
    with col2:
        file_type_options = ["text", "image", "pdf", "excel", "word", "audio", "video", "archive", "code", "other"]
        file_type = st.selectbox("File Type", file_type_options)
    
    submit_button = st.form_submit_button("Add File")
    
    if submit_button and file_name:
        # Check if file already exists
        if any(file["name"] == file_name for file in st.session_state.files):
            st.error(f"File '{file_name}' already exists!")
        else:
            # Add new file to the list
            new_file = {
                "name": file_name,
                "type": file_type,
                "size": get_random_size(),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.files.append(new_file)
            st.success(f"File '{file_name}' added successfully!")
            st.experimental_rerun()

# Display all files
st.header("All Files")

# Search functionality
search_query = st.text_input("Search files", placeholder="Enter file name to search")

# Filter files based on search query
filtered_files = st.session_state.files
if search_query:
    filtered_files = [file for file in st.session_state.files if search_query.lower() in file["name"].lower()]

# Sort options
sort_col1, sort_col2 = st.columns([1, 3])
with sort_col1:
    sort_by = st.selectbox("Sort by", ["name", "type", "size", "date"])
with sort_col2:
    sort_order = st.radio("Order", ["Ascending", "Descending"], horizontal=True)

# Sort files
if sort_by == "size":
    # Custom sorting for size (KB, MB)
    def extract_size(file):
        size_str = file["size"]
        value = float(size_str.split()[0])
        unit = size_str.split()[1]
        if unit == "MB":
            return value * 1024
        return value
    
    filtered_files = sorted(filtered_files, key=extract_size, reverse=(sort_order == "Descending"))
else:
    filtered_files = sorted(filtered_files, key=lambda x: x[sort_by], reverse=(sort_order == "Descending"))

# Display files as cards
if filtered_files:
    for file in filtered_files:
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.markdown(f"<div style='font-size: 3rem; text-align: center;'>{get_file_icon(file['type'])}</div>", unsafe_allow_html=True)
            with col2:
                st.subheader(file["name"])
                st.text(f"Type: {file['type'].capitalize()}")
                st.text(f"Size: {file['size']}")
                st.text(f"Date: {file['date']}")
            with col3:
                if st.button("Delete", key=f"delete_{file['name']}"):
                    st.session_state.files.remove(file)
                    st.success(f"File '{file['name']}' deleted successfully!")
                    st.experimental_rerun()
            st.markdown("---")
else:
    st.info("No files found. Add some files using the form above.")