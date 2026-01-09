# Server Setup Guide

Complete guide for running the Agentic Coder server for remote client access.

## Quick Start

### Linux / macOS

```bash
# Make script executable
chmod +x start_server.sh

# Start server
./start_server.sh
```

### Windows

```cmd
# Run the batch file
start_server.bat
```

The server will start on `http://0.0.0.0:8000` and be accessible from other machines on your network.

---

## Manual Setup

If you prefer to configure manually:

### 1. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
nano .env  # or any text editor
```

**Required settings:**
```bash
# LLM Configuration
LLM_ENDPOINT=http://localhost:8001/v1  # Your vLLM server
LLM_API_KEY=your-api-key-here
LLM_MODEL=deepseek-ai/DeepSeek-R1

# Workspace
DEFAULT_WORKSPACE=/path/to/your/workspace

# Optional: Load Balancing (multiple vLLM servers)
# VLLM_ENDPOINTS=http://server1:8001/v1,http://server2:8001/v1
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Server

**For Local Access Only (default):**
```bash
cd backend
uvicorn app.main:app --port 8000 --reload
```
> ⚠️ This only allows connections from localhost (127.0.0.1)

**For Remote Access (recommended for remote client):**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
> ✅ This allows connections from other machines on your network

### 4. Verify Server is Running

Open your browser and check:
- Health check: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

For remote access, use your server's IP address:
- `http://192.168.1.100:8000/health` (replace with your IP)

---

## Network Configuration

### Finding Your Server IP

**Linux:**
```bash
hostname -I | awk '{print $1}'
# or
ip addr show | grep "inet " | grep -v 127.0.0.1
```

**macOS:**
```bash
ipconfig getifaddr en0
# or for WiFi
ipconfig getifaddr en1
```

**Windows:**
```cmd
ipconfig | findstr "IPv4"
```

### Firewall Configuration

If remote clients cannot connect, you may need to allow port 8000:

**Linux (UFW):**
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

**Linux (firewalld):**
```bash
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

**Windows:**
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Agentic Coder" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

**macOS:**
Firewall is usually disabled by default. If enabled:
- System Preferences → Security & Privacy → Firewall → Firewall Options
- Add Python/uvicorn to allowed apps

---

## Testing Remote Connection

### From Remote Client

1. **Download the remote client binary** for your platform from [Releases](https://github.com/KIMSUNGHOON/agentic-coder/releases)

2. **Run the client:**
   ```bash
   # Linux/macOS
   ./agentic-coder-client-linux 192.168.1.100 8000

   # Windows
   agentic-coder-client-windows.exe 192.168.1.100 8000
   ```
   Replace `192.168.1.100` with your server's IP address.

3. **Check health status:**
   The client will automatically perform a health check. You should see:
   ```
   ✓ Server is healthy
   Version: 1.0.0
   ```

### Using curl

Quick test from command line:
```bash
# Health check
curl http://192.168.1.100:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0","components":{...}}
```

---

## Production Deployment

For production environments, use a production ASGI server:

### Using Gunicorn + Uvicorn Workers

```bash
# Install gunicorn
pip install gunicorn

# Start with 4 workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

### Using systemd (Linux)

Create `/etc/systemd/system/agentic-coder.service`:

```ini
[Unit]
Description=Agentic Coder Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/agentic-coder/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable agentic-coder
sudo systemctl start agentic-coder
sudo systemctl status agentic-coder
```

### Using Docker

```bash
# Build image
docker build -t agentic-coder .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v /path/to/workspace:/workspace \
  --name agentic-coder \
  agentic-coder
```

---

## Troubleshooting

### Client Cannot Connect

**Check 1: Server is running**
```bash
curl http://localhost:8000/health
```
If this fails, the server is not running.

**Check 2: Server is binding to 0.0.0.0**
```bash
# Check what uvicorn is bound to
netstat -tuln | grep 8000
# or
ss -tuln | grep 8000
```
You should see `0.0.0.0:8000`, not `127.0.0.1:8000`

**Check 3: Firewall allows port 8000**
```bash
# Linux
sudo ufw status | grep 8000

# Test from remote machine
telnet <server-ip> 8000
```

**Check 4: Network connectivity**
```bash
# From remote machine, ping server
ping <server-ip>

# Try accessing health endpoint
curl http://<server-ip>:8000/health
```

### Server Crashes on Startup

**Check logs:**
```bash
# See detailed error messages
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

**Common issues:**
- Missing `.env` file → Copy from `.env.example`
- Wrong LLM endpoint → Check `LLM_ENDPOINT` in `.env`
- Missing dependencies → Run `pip install -r requirements.txt`
- Port already in use → Change port or kill existing process

### GLIBC Version Error (Linux Client)

```
error: /lib/x86_64-linux-gnu/libm.so.6: version 'GLIBC_2.38' not found
```

**Solution 1: Use newer binaries** (from releases v1.0.1+)
- We now build on Ubuntu 20.04 for better compatibility

**Solution 2: Run from source instead**
```bash
git clone https://github.com/KIMSUNGHOON/agentic-coder.git
cd agentic-coder
pip install -r requirements.txt
python -m backend.cli.remote_client http://<server-ip>:8000
```

---

## Environment Variables Reference

Complete list of server configuration options:

```bash
# === LLM Configuration ===
LLM_ENDPOINT=http://localhost:8001/v1
LLM_API_KEY=your-api-key
LLM_MODEL=deepseek-ai/DeepSeek-R1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=8000

# === Load Balancing (Optional) ===
# Multiple endpoints for round-robin load balancing
VLLM_ENDPOINTS=http://server1:8001/v1,http://server2:8001/v1

# === Workspace ===
DEFAULT_WORKSPACE=/home/user/workspace

# === Server ===
LOG_LEVEL=INFO
CORS_ORIGINS=*

# === Database (Optional) ===
DATABASE_URL=sqlite:///./agentic_coder.db
```

---

## Security Considerations

### For Development

The startup scripts (`start_server.sh`, `start_server.bat`) are designed for **development and testing** on trusted networks.

### For Production

1. **Use HTTPS:** Set up reverse proxy (nginx, Caddy) with SSL/TLS
2. **Authentication:** Add API key authentication middleware
3. **Rate Limiting:** Prevent abuse with rate limiting
4. **Network Security:** Use VPN or firewall rules to restrict access
5. **Environment Variables:** Never commit `.env` to version control

---

## Next Steps

- ✅ Start the server using `./start_server.sh` or `start_server.bat`
- ✅ Download remote client from [Releases](https://github.com/KIMSUNGHOON/agentic-coder/releases)
- ✅ Connect from remote client using server IP:PORT
- ✅ See [Remote Client Guide](REMOTE_CLIENT_BINARY.md) for client usage

**Questions?** Open an issue at https://github.com/KIMSUNGHOON/agentic-coder/issues
