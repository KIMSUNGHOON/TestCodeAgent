@echo off
REM Agentic Coder Server Startup Script for Windows
REM Starts the FastAPI server accessible from external machines

echo.
echo 🚀 Starting Agentic Coder Server...
echo.

REM Check if .env exists
if not exist .env (
    echo ⚠️  Warning: .env file not found
    if exist .env.example (
        echo    Creating from .env.example...
        copy .env.example .env >nul
        echo ✓ Created .env - Please edit it with your configuration
        echo.
    ) else (
        echo ❌ Error: .env.example not found
        exit /b 1
    )
)

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    echo 📦 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install dependencies if needed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo 📥 Installing dependencies...
    pip install -r requirements.txt
)

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo ✅ Server Configuration:
echo    - Local access:    http://localhost:8000
echo    - Network access:  http://%LOCAL_IP%:8000
echo    - API docs:        http://localhost:8000/docs
echo    - Health check:    http://localhost:8000/health
echo.
echo 🌐 Server will be accessible from other machines on your network
echo    Use this for remote client: %LOCAL_IP%:8000
echo.
echo Press Ctrl+C to stop the server
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Start server with external access enabled
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
