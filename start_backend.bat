@echo off
echo Starting FSM Graph Visualizer Backend...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python main.py
pause

