import streamlit as st
import pandas as pd
from datetime import datetime

# Set page configuration
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

# Page title
st.title("📝 Text Manager")
st.caption("Add, delete, and view text notes")

# Initialize dummy notes if not already in session state
if "notes" not in st.session_state:
    st.session_state.notes = [
        {
            "title": "Welcome Note",
            "content": "Welcome to the Text Manager! This is a sample note to get you started.",
            "category": "general",
            "date": "2023-05-15"
        },
        {
            "title": "Shopping List",
            "content": "1. Milk\n2. Eggs\n3. Bread\n4. Apples\n5. Coffee",
            "category": "personal",
            "date": "2023-05-10"
        },
        {
            "title": "Meeting Notes",
            "content": "Project deadline: June 15\nTeam members: John, Sarah, Mike\nKey deliverables: UI design, backend API, documentation",
            "category": "work",
            "date": "2023-05-01"
        }
    ]

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
    
    if submit_button and note_title and note_content:
        # Check if note title already exists
        if any(note["title"] == note_title for note in st.session_state.notes):
            st.error(f"Note with title '{note_title}' already exists!")
        else:
            # Add new note to the list
            new_note = {
                "title": note_title,
                "content": note_content,
                "category": note_category,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.notes.append(new_note)
            st.success(f"Note '{note_title}' added successfully!")
            st.experimental_rerun()

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
filtered_notes = sorted(filtered_notes, key=lambda x: x[sort_by], reverse=(sort_order == "Descending"))

# Display notes
if filtered_notes:
    for note in filtered_notes:
        with st.expander(f"{note['title']} ({note['date']})"):
            st.markdown(f"**Category:** {get_category_badge(note['category'])}", unsafe_allow_html=True)
            st.markdown(f"<div class='note-content'>{note['content']}</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Delete", key=f"delete_{note['title']}"):
                    st.session_state.notes.remove(note)
                    st.success(f"Note '{note['title']}' deleted successfully!")
                    st.experimental_rerun()
                
                # Edit functionality
                if st.button("Edit", key=f"edit_{note['title']}"):
                    st.session_state.editing_note = note
                    st.experimental_rerun()
else:
    st.info("No notes found. Add some notes using the form above.")

# Edit note form (appears when editing a note)
if "editing_note" in st.session_state:
    st.header(f"Edit Note: {st.session_state.editing_note['title']}")
    with st.form("edit_note_form"):
        edited_title = st.text_input("Title", value=st.session_state.editing_note["title"])
        edited_content = st.text_area("Content", value=st.session_state.editing_note["content"], height=150)
        
        col1, col2 = st.columns(2)
        with col1:
            category_options = ["general", "personal", "work", "important"]
            edited_category = st.selectbox(
                "Category", 
                category_options, 
                index=category_options.index(st.session_state.editing_note["category"])
            )
        
        cancel_button = st.form_submit_button("Cancel")
        save_button = st.form_submit_button("Save Changes")
        
        if cancel_button:
            del st.session_state.editing_note
            st.experimental_rerun()
        
        if save_button:
            # Find the note in the list
            for i, note in enumerate(st.session_state.notes):
                if note == st.session_state.editing_note:
                    # Update the note
                    st.session_state.notes[i] = {
                        "title": edited_title,
                        "content": edited_content,
                        "category": edited_category,
                        "date": datetime.now().strftime("%Y-%m-%d")  # Update date to current
                    }
                    st.success(f"Note '{edited_title}' updated successfully!")
                    del st.session_state.editing_note
                    st.experimental_rerun()
                    break