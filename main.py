# main_improved.py - FastAPI WebSocket Chat with Proper Authentication
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import asyncio
import sqlite3
import os
import hashlib
import secrets
from pydantic import BaseModel

# Database Configuration
DATABASE_FILE = "chat.db"

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Create users table with password and session management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_online INTEGER DEFAULT 0
        )
    ''')
    
    # Create sessions table for managing active sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NULL,
            is_global INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (recipient_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

# Initialize database on startup
init_database()

# Pydantic models for API
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class MessageCreate(BaseModel):
    content: str
    recipient_username: Optional[str] = None

# FastAPI app initialization
app = FastAPI(title="WebSocket Chat App - With Authentication")
security = HTTPBearer(auto_error=False)

# =============================================================================
# AUTHENTICATION HELPER FUNCTIONS
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password with salt"""
    salt = secrets.token_bytes(32)  # Generate 32 random bytes for salt
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Store salt + hash as base64 for safe database storage
    import base64
    return base64.b64encode(salt + pwdhash).decode('utf-8')

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        import base64
        # Decode the stored password
        stored_bytes = base64.b64decode(stored_password.encode('utf-8'))
        
        # Extract salt (first 32 bytes) and hash (remaining bytes)
        salt = stored_bytes[:32]
        stored_hash = stored_bytes[32:]
        
        # Hash the provided password with the stored salt
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        
        # Compare hashes
        return pwdhash == stored_hash
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================

def get_db_connection():
    """Get a new database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def register_user(username: str, password: str):
    """Register a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Hash password and create user
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        
        # Get the created user
        cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user)
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

def login_user(username: str, password: str):
    """Authenticate user and create session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get user by username
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Login failed: User '{username}' not found")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        print(f"🔍 Verifying password for user: {username}")
        if not verify_password(user["password_hash"], password):
            print(f"❌ Login failed: Invalid password for user '{username}'")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        print(f"✅ Password verified for user: {username}")
        
        # Invalidate any existing sessions for this user
        cursor.execute(
            "UPDATE user_sessions SET is_active = 0 WHERE user_id = ? AND is_active = 1",
            (user["id"],)
        )
        
        # Create new session token
        session_token = generate_session_token()
        expires_at = datetime.utcnow() + timedelta(days=7)  # Session valid for 7 days
        
        cursor.execute(
            """INSERT INTO user_sessions (user_id, session_token, expires_at) 
               VALUES (?, ?, ?)""",
            (user["id"], session_token, expires_at)
        )
        
        # Update last login
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"],)
        )
        
        conn.commit()
        print(f"✅ New session created for user: {username}")
        
        return {
            "user_id": user["id"],
            "username": user["username"],
            "session_token": session_token,
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        conn.close()

def logout_user(session_token: str):
    """Logout user and invalidate session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Invalidate the session
        cursor.execute(
            "UPDATE user_sessions SET is_active = 0 WHERE session_token = ?",
            (session_token,)
        )
        conn.commit()
        print(f"✅ Session invalidated: {session_token[:8]}...")
        return True
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return False
    finally:
        conn.close()

def verify_session_token(session_token: str):
    """Verify a session token and return user info"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT u.id, u.username, s.expires_at 
               FROM user_sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.session_token = ? AND s.is_active = 1 AND s.expires_at > CURRENT_TIMESTAMP""",
            (session_token,)
        )
        session = cursor.fetchone()
        
        if session:
            return dict(session)
        return None
        
    finally:
        conn.close()

def set_user_online_status(user_id: int, is_online: bool):
    """Set user's online status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET is_online = ? WHERE id = ?",
        (1 if is_online else 0, user_id)
    )
    conn.commit()
    conn.close()

def get_user_by_username(username: str):
    """Get user by username"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, created_at, is_online FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user) if user else None

def get_all_users():
    """Get all users with their online status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, created_at, is_online FROM users ORDER BY created_at")
    users = cursor.fetchall()
    conn.close()
    
    return [dict(user) for user in users]

def save_message(content: str, sender_id: int, recipient_id: Optional[int] = None):
    """Save a message to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    is_global = 1 if recipient_id is None else 0
    
    cursor.execute(
        """INSERT INTO messages (content, sender_id, recipient_id, is_global) 
           VALUES (?, ?, ?, ?)""",
        (content, sender_id, recipient_id, is_global)
    )
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return message_id

def get_global_messages(limit: int = 50):
    """Get recent global messages"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT m.id, m.content, m.created_at, u.username as sender
           FROM messages m
           JOIN users u ON m.sender_id = u.id
           WHERE m.is_global = 1
           ORDER BY m.created_at DESC
           LIMIT ?""",
        (limit,)
    )
    
    messages = cursor.fetchall()
    conn.close()
    
    return [dict(msg) for msg in reversed(messages)]

# =============================================================================
# WEBSOCKET CONNECTION MANAGER - ENHANCED WITH REAL-TIME USER LIST UPDATES
# =============================================================================
class ConnectionManager:
    """
    Enhanced WebSocket connection manager with proper user list updates
    """
    
    def __init__(self):
        # Map session_token to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # Map session_token to user info
        self.user_sessions: Dict[str, dict] = {}
        # Map username to session_token for easy lookup
        self.username_to_session: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, session_token: str, user_info: dict):
        """Accept a new WebSocket connection with session authentication"""
        await websocket.accept()
        
        username = user_info["username"]
        user_id = user_info["id"]
        
        # If user was already connected, disconnect the old session
        if username in self.username_to_session:
            old_session = self.username_to_session[username]
            if old_session in self.active_connections:
                try:
                    await self.active_connections[old_session].close()
                except:
                    pass
                del self.active_connections[old_session]
                del self.user_sessions[old_session]
        
        # Store the new connection
        self.active_connections[session_token] = websocket
        self.user_sessions[session_token] = user_info
        self.username_to_session[username] = session_token
        
        # Set user as online in database
        set_user_online_status(user_id, True)
        
        print(f"✅ WebSocket connected for user: {username} (session: {session_token[:8]}...)")
        print(f"📊 Total active connections: {len(self.active_connections)}")
        
        # CRITICAL: Broadcast updated user list to ALL connected users
        await self.broadcast_user_list_update(f"{username} joined the chat")
    
    def disconnect(self, session_token: str):
        """Remove a user's WebSocket connection"""
        if session_token in self.active_connections:
            user_info = self.user_sessions.get(session_token)
            username = user_info["username"] if user_info else "Unknown"
            user_id = user_info["id"] if user_info else None
            
            # Remove from tracking
            del self.active_connections[session_token]
            del self.user_sessions[session_token]
            
            if username in self.username_to_session:
                del self.username_to_session[username]
            
            # Set user as offline in database
            if user_id:
                set_user_online_status(user_id, False)
            
            print(f"❌ WebSocket disconnected for user: {username}")
            print(f"📊 Total active connections: {len(self.active_connections)}")
            
            return username
        return None
    
    async def send_personal_message(self, message: str, username: str):
        """Send a message to a specific user by username"""
        session_token = self.username_to_session.get(username)
        if session_token and session_token in self.active_connections:
            websocket = self.active_connections[session_token]
            try:
                await websocket.send_text(message)
                return True
            except Exception as e:
                print(f"❌ Failed to send message to {username}: {e}")
                self.disconnect(session_token)
                return False
        else:
            print(f"⚠️ User {username} not connected")
            return False
    
    async def broadcast(self, message: str, exclude_session: Optional[str] = None):
        """Send a message to all connected users"""
        print(f"📢 Broadcasting message to {len(self.active_connections)} users")
        
        failed_sessions = []
        
        for session_token, websocket in self.active_connections.items():
            if exclude_session and session_token == exclude_session:
                continue
            
            try:
                await websocket.send_text(message)
            except Exception as e:
                user_info = self.user_sessions.get(session_token, {})
                username = user_info.get("username", "Unknown")
                print(f"❌ Failed to send message to {username}: {e}")
                failed_sessions.append(session_token)
        
        # Clean up failed connections
        for session_token in failed_sessions:
            self.disconnect(session_token)
    
    async def broadcast_user_list_update(self, message: str = None):
        """
        CRITICAL FUNCTION: Broadcast updated user list to all connected users
        This ensures the user list is always up-to-date in real-time
        """
        online_users = self.get_active_users()
        
        user_list_update = {
            "type": "user_list_update",
            "users": online_users,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        print(f"📋 Broadcasting user list update: {len(online_users)} users online")
        await self.broadcast(json.dumps(user_list_update))
    
    def get_active_users(self) -> List[str]:
        """Get list of all currently connected usernames"""
        return [user_info["username"] for user_info in self.user_sessions.values()]
    
    def is_user_online(self, username: str) -> bool:
        """Check if a specific user is currently connected"""
        return username in self.username_to_session
    
    def get_user_info_by_session(self, session_token: str) -> Optional[dict]:
        """Get user info by session token"""
        return self.user_sessions.get(session_token)

# Create the global connection manager instance
manager = ConnectionManager()

# =============================================================================
# AUTHENTICATION DEPENDENCY
# =============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user from session token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    session_info = verify_session_token(credentials.credentials)
    if not session_info:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return session_info

# =============================================================================
# HTTP ENDPOINTS - WITH PROPER AUTHENTICATION
# =============================================================================

@app.post("/register")
async def register_endpoint(user_data: UserRegister):
    """Register a new user"""
    try:
        # Validate input
        username = user_data.username.strip()
        password = user_data.password
        
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        
        if len(username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
        
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        print(f"🔄 Attempting to register user: {username}")
        
        db_user = register_user(username, password)
        
        print(f"✅ User registered successfully: {username}")
        
        return {
            "message": "User registered successfully",
            "user": {
                "id": db_user["id"],
                "username": db_user["username"],
                "created_at": db_user["created_at"]
            }
        }
    except HTTPException as e:
        print(f"❌ Registration failed for '{user_data.username}': {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Debug endpoint to help troubleshoot authentication issues
@app.get("/debug/users")
async def debug_users():
    """Debug endpoint to check user registration (remove in production)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, username, created_at FROM users ORDER BY created_at DESC LIMIT 10")
        users = cursor.fetchall()
        
        return {
            "total_users": len(users),
            "recent_users": [dict(user) for user in users]
        }
    finally:
        conn.close()

@app.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to check active sessions (remove in production)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT s.id, s.user_id, u.username, s.created_at, s.expires_at, s.is_active
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC LIMIT 20
        """)
        sessions = cursor.fetchall()
        
        return {
            "total_sessions": len(sessions),
            "recent_sessions": [dict(session) for session in sessions]
        }
    finally:
        conn.close()

# Debug endpoint to reset database (remove in production)
@app.post("/debug/reset")
async def debug_reset_database():
    """Reset the database (remove in production)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clear all tables
        cursor.execute("DELETE FROM user_sessions")
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM users")
        
        conn.commit()
        conn.close()
        
        print("🗑️ Database reset completed")
        
        return {"message": "Database reset successfully"}
    except Exception as e:
        print(f"❌ Database reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login_endpoint(user_data: UserLogin):
    """Login user and create session"""
    try:
        session_info = login_user(user_data.username, user_data.password)
        return {
            "message": "Login successful",
            "session_token": session_info["session_token"],
            "user": {
                "id": session_info["user_id"],
                "username": session_info["username"]
            },
            "expires_at": session_info["expires_at"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users")
async def get_users_endpoint(current_user: dict = Depends(get_current_user)):
    """Get all users with their online status"""
    try:
        users = get_all_users()
        user_list = []
        
        for user in users:
            user_list.append({
                "id": user["id"],
                "username": user["username"],
                "is_online": manager.is_user_online(user["username"]),
                "created_at": user["created_at"]
            })
        
        return user_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages/global")
async def get_global_messages_endpoint(current_user: dict = Depends(get_current_user)):
    """Get recent global messages"""
    try:
        messages = get_global_messages(50)
        result = []
        
        for msg in messages:
            result.append({
                "id": msg["id"],
                "content": msg["content"],
                "sender": msg["sender"],
                "created_at": msg["created_at"],
                "is_global": True
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logout")
async def logout_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and invalidate session"""
    if not credentials:
        raise HTTPException(status_code=401, detail="No session token provided")
    
    try:
        # Invalidate the session
        logout_success = logout_user(credentials.credentials)
        
        if logout_success:
            return {"message": "Logged out successfully"}
        else:
            return {"message": "Logout completed (session may have already been invalid)"}
            
    except Exception as e:
        print(f"❌ Logout endpoint error: {e}")
        # Return success anyway since logout should always work
        return {"message": "Logged out successfully"}

# =============================================================================
# WEBSOCKET ENDPOINT - WITH AUTHENTICATION
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    Enhanced WebSocket endpoint with session-based authentication
    URL: ws://localhost:8000/ws?token=SESSION_TOKEN
    """
    
    # Verify session token
    session_info = verify_session_token(token)
    if not session_info:
        await websocket.close(code=4001, reason="Invalid or expired session token")
        return
    
    user_info = {
        "id": session_info["id"],
        "username": session_info["username"]
    }
    
    # Register WebSocket connection
    await manager.connect(websocket, token, user_info)
    
    try:
        # Listen for messages from this client
        while True:
            data = await websocket.receive_text()
            print(f"📨 Received message from {user_info['username']}: {data}")
            
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid message format"
                }))
                continue
            
            # Process different types of messages
            message_type = message_data.get("type", "chat")
            content = message_data.get("content", "")
            recipient = message_data.get("recipient")
            
            if message_type == "chat":
                # Get recipient user ID if it's a private message
                recipient_id = None
                if recipient:
                    recipient_user = get_user_by_username(recipient)
                    if recipient_user:
                        recipient_id = recipient_user["id"]
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"User {recipient} not found"
                        }))
                        continue
                
                # Save message to database
                try:
                    save_message(content, user_info["id"], recipient_id)
                except Exception as e:
                    print(f"❌ Failed to save message: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Failed to save message"
                    }))
                    continue
                
                # Prepare message for broadcasting
                broadcast_message = {
                    "type": "chat",
                    "content": content,
                    "sender": user_info["username"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_global": recipient is None,
                    "recipient": recipient
                }
                
                if recipient is None:
                    # Global message: Send to all connected users
                    print(f"🌍 Broadcasting global message from {user_info['username']}")
                    await manager.broadcast(json.dumps(broadcast_message))
                else:
                    # Private message: Send to specific user + sender confirmation
                    print(f"💬 Sending private message from {user_info['username']} to {recipient}")
                    
                    # Send to recipient
                    success = await manager.send_personal_message(json.dumps(broadcast_message), recipient)
                    
                    # Send confirmation to sender
                    confirmation_message = broadcast_message.copy()
                    confirmation_message["type"] = "chat_sent"
                    confirmation_message["delivered"] = success
                    await websocket.send_text(json.dumps(confirmation_message))
            
            elif message_type == "typing":
                # Handle typing indicators
                typing_message = {
                    "type": "typing",
                    "username": user_info["username"],
                    "is_typing": message_data.get("is_typing", False),
                    "recipient": recipient
                }
                
                if recipient:
                    await manager.send_personal_message(json.dumps(typing_message), recipient)
                else:
                    await manager.broadcast(json.dumps(typing_message), exclude_session=token)
            
            elif message_type == "request_user_list":
                # Send current user list to requesting client
                await manager.broadcast_user_list_update()
    
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {user_info['username']}")
        username = manager.disconnect(token)
        
        if username:
            # Broadcast user list update when someone disconnects
            await manager.broadcast_user_list_update(f"{username} left the chat")
    
    except Exception as e:
        print(f"❌ WebSocket error for {user_info['username']}: {e}")
        username = manager.disconnect(token)
        
        if username:
            await manager.broadcast_user_list_update(f"{username} disconnected due to error")

# =============================================================================
# SERVE THE HTML FRONTEND
# =============================================================================

@app.get("/")
async def get():
    """Serve the HTML frontend"""
    try:
        with open("templates/chat.html", "r") as f:
            return HTMLResponse(content=f.read(), media_type="text/html")
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: templates/chat.html not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI WebSocket Chat Server (With Authentication)")
    print("📊 Database file:", DATABASE_FILE)
    print("🔐 Authentication: Enabled")
    print("🌐 Server will be available at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)