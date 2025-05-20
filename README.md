# Install dependencies using Poetry
poetry install

# Activate virtual env
poetry env activate

# Start the FastAPI
poetry run uvicorn main:app --reload