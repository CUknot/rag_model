import streamlit as st
import requests # Used for making HTTP requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
FASTAPI_BASE_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Text Manager",
    page_icon="📝",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.note-card {
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #ddd;
    margin-bottom: 1rem;
}
.note-content {
    white-space: pre-wrap;
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    font-family: monospace;
}
.category-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 1rem;
    font-size: 0.8rem;
    margin-right: 0.5rem;
}
.category-general {
    background-color: #e9ecef;
    color: #495057;
}
.category-personal {
    background-color: #d1ecf1;
    color: #0c5460;
}
.category-work {
    background-color: #d4edda;
    color: #155724;
}
.category-important {
    background-color: #f8d7da;
    color: #721c24;
}
</style>
""", unsafe_allow_html=True)

# --- FastAPI Helper Functions ---

def get_notes_from_backend():
    """Fetches all notes from the FastAPI backend."""
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/files/")
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to FastAPI backend at {FASTAPI_BASE_URL}. Please ensure it's running.")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching notes: {e}")
        return []

def add_note_to_backend(title, content, category):
    """Sends a new note to the FastAPI backend. Date is handled by the backend."""
    note_data = {
        "title": title,
        "content": content,
        "category": category,
        # "date": datetime.now().strftime("%Y-%m-%d") # Removed: Date is now set by FastAPI backend
    }
    try:
        response = requests.post(f"{FASTAPI_BASE_URL}/upload-text/", json=note_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error adding note: {e}")
        # Print the detailed error from FastAPI if available
        if response is not None:
            try:
                st.error(f"FastAPI response: {response.json()}")
            except requests.exceptions.JSONDecodeError:
                st.error(f"FastAPI raw response: {response.text}")
        return None

def delete_note_from_backend(title: str):
    """Deletes a note from the FastAPI backend by title."""
    try:
        # FastAPI's delete endpoint now expects 'title' as a query parameter
        response = requests.delete(f"{FASTAPI_BASE_URL}/files/", params={"title": title})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting note: {e}")
        if response is not None:
            try:
                st.error(f"FastAPI response: {response.json()}")
            except requests.exceptions.JSONDecodeError:
                st.error(f"FastAPI raw response: {response.text}")
        return None

def update_note_in_backend(original_title, new_title, new_content, new_category):
    """Updates an existing note in the FastAPI backend."""
    updated_data = {
        "title": new_title,
        "content": new_content,
        "category": new_category,
        # "date": datetime.now().strftime("%Y-%m-%d") # Removed: Date is now set by FastAPI backend upon update
    }
    try:
        response = requests.put(f"{FASTAPI_BASE_URL}/files/{original_title}", json=updated_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating note: {e}")
        if response is not None:
            try:
                st.error(f"FastAPI response: {response.json()}")
            except requests.exceptions.JSONDecodeError:
                st.error(f"FastAPI raw response: {response.text}")
        return None

# --- Streamlit App Logic ---

# Page title
st.title("📝 Text Manager")
st.caption("Add, delete, and view text notes")

# Initialize notes by fetching from backend on app load
# Use a custom key to prevent re-fetching on minor widget interactions
if "notes_data_loaded" not in st.session_state:
    st.session_state.notes = get_notes_from_backend()
    st.session_state.notes_data_loaded = True

# Function to get category badge HTML
def get_category_badge(category):
    return f'<span class="category-badge category-{category}">{category.capitalize()}</span>'

# Add new note section
st.header("Add New Note")
with st.form("add_note_form"):
    note_title = st.text_input("Title", placeholder="Enter note title")
    note_content = st.text_area("Content", placeholder="Enter your text here...", height=150)

    col1, col2 = st.columns(2)
    with col1:
        category_options = ["general", "personal", "work", "important"]
        note_category = st.selectbox("Category", category_options)

    submit_button = st.form_submit_button("Add Note")

    if submit_button: # Check if button is pressed first
        if not note_title.strip() or not note_content.strip():
            st.error("Title and Content cannot be empty.")
        else:
            # Check for title existence more robustly (via backend, or rely on backend's 409)
            # For this setup, FastAPI handles the 409 conflict, so no need for client-side check
            add_response = add_note_to_backend(note_title, note_content, note_category)
            if add_response: # Check for a successful response (not None)
                st.success(f"Note '{note_title}' added successfully!")
                st.session_state.notes = get_notes_from_backend() # Refresh notes from backend
                st.session_state.editing_note = None # Clear editing state if it was active
                st.rerun()
            # Error messages are handled inside add_note_to_backend now

# Display all notes
st.header("All Notes")

# Search functionality
search_query = st.text_input("Search notes", placeholder="Enter title or content to search")

# Filter notes based on search query
filtered_notes = st.session_state.notes
if search_query:
    filtered_notes = [
        note for note in st.session_state.notes
        if search_query.lower() in note["title"].lower() or search_query.lower() in note["content"].lower()
    ]

# Category filter
category_filter = st.multiselect(
    "Filter by category",
    options=["general", "personal", "work", "important"],
    default=[]
)

if category_filter:
    filtered_notes = [note for note in filtered_notes if note["category"] in category_filter]

# Sort options
sort_col1, sort_col2 = st.columns([1, 3])
with sort_col1:
    sort_by = st.selectbox("Sort by", ["title", "date", "category"])
with sort_col2:
    sort_order = st.radio("Order", ["Ascending", "Descending"], horizontal=True)

# Sort notes
# Ensure 'date' is sortable (if stored as string, YYYY-MM-DD is good)
if sort_by == "date":
    filtered_notes = sorted(filtered_notes, key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"), reverse=(sort_order == "Descending"))
else:
    filtered_notes = sorted(filtered_notes, key=lambda x: x[sort_by], reverse=(sort_order == "Descending"))


# Display notes
if filtered_notes:
    for note in filtered_notes:
        with st.expander(f"{note['title']} ({note['date']})"):
            st.markdown(f"**Category:** {get_category_badge(note['category'])}", unsafe_allow_html=True)
            st.markdown(f"<div class='note-content'>{note['content']}</div>", unsafe_allow_html=True)

            col1, col2 = st.columns([3, 1])
            with col2:
                # Use a unique key for each delete button to prevent issues
                if st.button("Delete", key=f"delete_{note['title']}_{note['date']}"):
                    delete_response = delete_note_from_backend(note['title'])
                    if delete_response: # Check for successful response
                        st.success(f"Note '{note['title']}' deleted successfully!")
                        st.session_state.notes = get_notes_from_backend() # Refresh notes
                        st.rerun()
                    # Error messages are handled inside delete_note_from_backend now

                # Edit functionality
                # Use a unique key for each edit button
                if st.button("Edit", key=f"edit_{note['title']}_{note['date']}"):
                    st.session_state.editing_note = note
                    st.rerun()
else:
    st.info("No notes found. Add some notes using the form above.")

# Edit note form (appears when editing a note)
if "editing_note" in st.session_state and st.session_state.editing_note is not None:
    st.header(f"Edit Note: {st.session_state.editing_note['title']}")
    with st.form("edit_note_form"):
        original_title = st.session_state.editing_note["title"]
        edited_title = st.text_input("Title", value=st.session_state.editing_note["title"])
        edited_content = st.text_area("Content", value=st.session_state.editing_note["content"], height=150)

        col1, col2 = st.columns(2)
        with col1:
            category_options = ["general", "personal", "work", "important"]
            # Safely get index for selectbox, default to 0 if category not found
            try:
                selected_index = category_options.index(st.session_state.editing_note["category"])
            except ValueError:
                selected_index = 0 # Default to 'general' if category is unexpected

            edited_category = st.selectbox(
                "Category",
                category_options,
                index=selected_index
            )

        cancel_button = st.form_submit_button("Cancel")
        save_button = st.form_submit_button("Save Changes")

        if cancel_button:
            del st.session_state.editing_note
            st.rerun()

        if save_button:
            if not edited_title.strip() or not edited_content.strip():
                st.error("Title and Content cannot be empty.")
            else:
                update_response = update_note_in_backend(original_title, edited_title, edited_content, edited_category)
                if update_response:
                    st.success(f"Note '{edited_title}' updated successfully!")
                    del st.session_state.editing_note
                    st.session_state.notes = get_notes_from_backend() # Refresh notes
                    st.rerun()
                # Error messages are handled inside update_note_in_backend now