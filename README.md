# 🚀 WebSocket Chat Application

A real-time chat application built with **FastAPI**, **WebSockets**, and **SQLite** featuring user authentication, private messaging, and live user presence.

![Python](https://img.shields.io/badge/python-v3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

### 🔐 **Authentication System**
- User registration with username and password
- Secure password hashing (PBKDF2 with salt)
- Session-based authentication with JWT-like tokens
- Persistent login sessions (7-day expiration)
- Multiple device login support

### 💬 **Real-time Messaging**
- **Global Chat**: Public messages visible to all users
- **Private Messaging**: Direct messages between users
- **Live Typing Indicators**: See when someone is typing
- **Message History**: Persistent message storage
- **Real-time Delivery**: Instant message delivery via WebSockets

### 👥 **User Management**
- **Live User List**: Real-time online/offline status
- **User Presence**: Instant updates when users join/leave
- **Connection Management**: Graceful handling of disconnections
- **Auto-reconnection**: Automatic reconnection on network issues

### 🎨 **Modern UI/UX**
- Clean, responsive design
- Real-time connection status indicators
- Typing indicators and notifications
- Smooth transitions and animations
- Mobile-friendly interface

## 🏗️ **Architecture**

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│                 │ ←──────────────→ │                 │
│   Frontend      │                  │   FastAPI       │
│   (HTML/JS)     │    HTTP API      │   Backend       │
│                 │ ←──────────────→ │                 │
└─────────────────┘                  └─────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │   SQLite DB     │
                                     │   (Users,       │
                                     │   Messages,     │
                                     │   Sessions)     │
                                     └─────────────────┘
```

### **WebSocket Flow**
1. **Authentication**: Client connects with session token
2. **Connection Management**: Server tracks active connections
3. **Message Broadcasting**: Real-time message distribution
4. **User List Sync**: Live user presence updates

## 🚀 **Quick Start**

### **Option 1: Using Docker (Recommended)**

```bash
# Clone the repository
git clone https://github.com/khapchi/websocket-chat-app.git
cd websocket-chat-app

# Build and run with Docker
docker build -t websocket-chat .
docker run -p 8000:8000 websocket-chat
```

### **Option 2: Local Development**

```bash
# Clone the repository
git clone https://github.com/khapchi/websocket-chat-app.git
cd websocket-chat-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **Option 3: Docker Compose**

```bash
# Clone and run with docker-compose
git clone https://github.com/khapchi/websocket-chat-app.git
cd websocket-chat-app
docker-compose up --build
```

**Open your browser and go to:** `http://localhost:8000`

## 📁 **Project Structure**

```
websocket-chat-app/
├── main.py              # Enhanced backend with authentication
├── main_simple.py               # Pure SQLite version (no SQLAlchemy)
├── main.py                      # Original version
├── templates/
│   ├── chat_improved.html       # Enhanced frontend with login/register
│   └── chat.html               # Original frontend
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── troubleshoot.py              # Database troubleshooting tool
├── .gitignore                   # Git ignore file
├── .dockerignore               # Docker ignore file
└── README.md                   # This file
```

## 🔧 **Configuration**

### **Environment Variables**

Create a `.env` file (optional):

```env
# Database
DATABASE_URL=sqlite:///./chat.db

# Security
SESSION_EXPIRE_DAYS=7

# Server
HOST=0.0.0.0
PORT=8000
```

### **Database Configuration**

**SQLite (Default)**:
```python
DATABASE_FILE = "chat.db"  # Auto-created
```

**PostgreSQL (Production)**:
```python
DATABASE_URL = "postgresql://username:password@localhost/chatdb"
```

## 📡 **API Documentation**

### **Authentication Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register` | Register new user |
| `POST` | `/login` | User login |
| `POST` | `/logout` | User logout |

### **Chat Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users` | Get all users with status |
| `GET` | `/messages/global` | Get global message history |

### **WebSocket Endpoint**

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| `WebSocket` | `/ws?token=SESSION_TOKEN` | Real-time chat connection |

### **Message Types**

**Chat Message**:
```json
{
  "type": "chat",
  "content": "Hello world!",
  "recipient": "username" // null for global
}
```

**Typing Indicator**:
```json
{
  "type": "typing",
  "is_typing": true,
  "recipient": "username" // null for global
}
```

## 🛠️ **Development**

### **Running Tests**

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### **Code Quality**

```bash
# Install linting tools
pip install black flake8 mypy

# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### **Database Management**

```bash
# Reset database
python troubleshoot.py

# Or manually
rm chat.db
uvicorn main:app --reload
```

## 🐳 **Docker Deployment**

### **Production Deployment**

```bash
# Build production image
docker build -t websocket-chat:latest .

# Run with environment variables
docker run -d \
  --name chat-app \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/chat \
  websocket-chat:latest
```

### **Docker Compose (with PostgreSQL)**

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/chatdb
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=chatdb
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🔍 **Troubleshooting**

### **Common Issues**

**1. Authentication Error (401 Unauthorized)**
```bash
# Reset database
python troubleshoot.py
# Choose option 3 to reset database
```

**2. WebSocket Connection Failed**
```bash
# Check if server is running
curl http://localhost:8000/

# Check firewall settings
# Ensure port 8000 is open
```

**3. User List Not Updating**
```bash
# Clear browser cache and localStorage
# Restart the server
```

### **Debug Endpoints** (Development Only)

- `GET /debug/users` - View registered users
- `GET /debug/sessions` - View active sessions  
- `POST /debug/reset` - Reset database

## 📚 **Documentation**

### **WebSocket Message Flow**

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant D as Database
    
    C->>S: Connect with session token
    S->>D: Verify session
    D->>S: Session valid
    S->>C: Connection accepted
    
    C->>S: Send chat message
    S->>D: Save message
    S->>C: Broadcast to all clients
    
    Note over C,S: Real-time bidirectional communication
```

### **Authentication Flow**

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant D as Database
    
    U->>F: Register/Login
    F->>B: POST /login
    B->>D: Verify credentials
    D->>B: User validated
    B->>F: Session token
    F->>B: WebSocket connect with token
    B->>F: Authenticated connection
```

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### **Development Guidelines**

- Follow PEP 8 for Python code style
- Add comments for WebSocket and authentication logic
- Include tests for new features
- Update documentation for API changes

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 **Roadmap**

- [ ] **Message Reactions** (👍, ❤️, 😄)
- [ ] **File Upload/Sharing**
- [ ] **Chat Rooms/Channels**
- [ ] **Message Search**
- [ ] **User Profiles & Avatars**
- [ ] **Push Notifications**
- [ ] **Mobile App** (React Native)
- [ ] **Video/Voice Calls** (WebRTC)

## 🏆 **Features Comparison**

| Feature | Basic Version | Enhanced Version |
|---------|---------------|------------------|
| Authentication | ❌ | ✅ Full system |
| Session Management | ❌ | ✅ Persistent |
| Real-time User List | ❌ | ✅ Live updates |
| Private Messaging | ✅ | ✅ Enhanced |
| Message History | ✅ | ✅ Persistent |
| Security | ❌ | ✅ Password hashing |
| Multiple Logins | ❌ | ✅ Supported |
| Auto-reconnection | ✅ | ✅ Enhanced |

## 💡 **Technical Highlights**

### **WebSocket Implementation**
- **Connection Management**: Centralized WebSocket connection tracking
- **Message Broadcasting**: Efficient real-time message distribution
- **Error Handling**: Graceful connection failures and recovery
- **Authentication**: Session-based WebSocket authentication

### **Security Features**
- **Password Hashing**: PBKDF2 with 32-byte salt
- **Session Tokens**: Secure random token generation
- **SQL Injection Protection**: Parameterized queries
- **XSS Prevention**: HTML entity escaping

### **Performance Optimizations**
- **Efficient Broadcasting**: Minimal message duplication
- **Connection Pooling**: Reusable database connections
- **Memory Management**: Proper cleanup of disconnected users
- **Auto-reconnection**: Seamless user experience

## 🌟 **Star History**

If you find this project useful, please give it a ⭐ on GitHub!


**Built with ❤️ using FastAPI and WebSockets**