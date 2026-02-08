#!/bin/bash

# Ensure we are using the python from the virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please create one with 'python3 -m venv venv' and install requirements."
    exit 1
fi

echo "Starting FastAPI Backend..."
python -m uvicorn api:app --reload --port 8000 &
API_PID=$!

echo "Starting Streamlit App..."
python -m streamlit run app.py &
STREAMLIT_PID=$!

function cleanup {
    echo "Stopping services..."
    kill $API_PID
    kill $STREAMLIT_PID
}

trap cleanup EXIT

echo "Services started. Press Ctrl+C to stop."
wait
