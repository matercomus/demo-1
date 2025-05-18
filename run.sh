#!/usr/bin/env bash

# Start FastAPI backend
echo "Starting FastAPI backend on http://localhost:8000 ..."
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start Python HTTP server for frontend
cd frontend
echo "Serving frontend on http://localhost:3000 ..."
python3 -m http.server 3000 &
FRONTEND_PID=$!
cd ..

# Trap Ctrl+C and kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID" SIGINT

# Wait for both background jobs
wait $BACKEND_PID $FRONTEND_PID 