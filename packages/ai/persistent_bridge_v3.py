#!/usr/bin/env python3
"""
Persistent Hermes Bridge v3
- JSON corruption fix
- Session isolation per user
- Safe JSON extraction with retry
"""

import os
import sys
import json
import subprocess
import asyncio
import threading
import time
import re
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# Global session manager
class BridgeManager:
    """Manages isolated bridge sessions per user"""
    
    def __init__(self):
        self.sessions: Dict[str, 'HermesBridge'] = {}
        self.lock = threading.Lock()
    
    def get_session(self, session_id: str) -> 'HermesBridge':
        """Get or create isolated session"""
        with self.lock:
            if session_id not in self.sessions:
                bridge = HermesBridge(session_id=session_id)
                bridge.start()
                self.sessions[session_id] = bridge
                print(f"🆕 New session: {session_id}")
            return self.sessions[session_id]
    
    def destroy_session(self, session_id: str):
        """Destroy a session"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].stop()
                del self.sessions[session_id]
                print(f"🗑️  Destroyed session: {session_id}")
    
    def reset_session(self, session_id: str) -> 'HermesBridge':
        """Reset session (destroy + recreate)"""
        self.destroy_session(session_id)
        return self.get_session(session_id)


class HermesBridge:
    """Single isolated Hermes session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.process = None
        self.ready = False
        self.output_buffer = []
        self.buffer_lock = threading.Lock()
        self.reader_thread = None
    
    def start(self):
        """Start fresh Hermes session"""
        cmd = [
            "/home/siddhi/.local/bin/hermes",
            "chat",
            "--model", "kimi-for-coding",
            "--provider", "kimi-coding"
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd="/home/siddhi"
        )
        
        # Start reader thread
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        
        # Wait for initialization
        time.sleep(3)
        self.ready = True
    
    def _read_output(self):
        """Read output continuously"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    with self.buffer_lock:
                        self.output_buffer.append(line)
            except:
                break
    
    def send(self, message: str) -> str:
        """Send message and return clean response"""
        if not self.ready or not self.process:
            raise Exception("Bridge not ready")
        
        # Record buffer length before sending
        with self.buffer_lock:
            start_len = len(self.output_buffer)
        
        # Send message
        self.process.stdin.write(message + "\n")
        self.process.stdin.flush()
        
        # Wait for response with timeout
        start_time = time.time()
        timeout = 25  # Increased for Hermes response generation
        
        while time.time() - start_time < timeout:
            time.sleep(1)  # Check less frequently
            
            with self.buffer_lock:
                current_len = len(self.output_buffer)
            
            if current_len > start_len:
                # Wait more for complete response
                time.sleep(3)
                
                with self.buffer_lock:
                    new_lines = self.output_buffer[start_len:]
                    new_output = "".join(new_lines)
                
                return self._extract_response(new_output)
        
        return "Timeout"
    
    def _extract_response(self, raw_output: str) -> str:
        """Extract clean response with JSON safety"""
        
        # Remove ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', raw_output)
        
        # Strategy 1: Find and fix JSON
        json_result = self._extract_json_safe(cleaned)
        if json_result:
            return json_result
        
        # Strategy 2: Find content lines (actual response text)
        lines = cleaned.split('\n')
        content_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip UI artifacts and short lines
            if (len(stripped) > 20 and 
                not any(x in stripped for x in [
                    'kimi-for-coding', 'msg=interrupt', '⚕', '⏱', '⏲',
                    '───', '❯', 'Available Tools', 'Available Skills',
                    'Session:', 'Duration:', 'Messages:', 'Resume',
                    'Initializing agent...'
                ])):
                content_lines.append(stripped)
        
        if content_lines:
            # Return the longest content line (most likely the response)
            return max(content_lines, key=len)
        
        # Fallback: return cleaned text
        return cleaned.strip()[:500]
    
    def _extract_json_safe(self, text: str) -> Optional[str]:
        """Safely extract JSON with corruption handling"""
        
        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}')
        
        if start == -1 or end == -1 or end < start:
            return None
        
        json_str = text[start:end+1]
        
        # Fix common corruption patterns
        json_str = json_str.replace('\n', ' ')
        json_str = json_str.replace('\r', '')
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # Remove trailing commas
        
        # Validate JSON
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            return None
    
    def stop(self):
        """Stop the bridge"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.ready = False


# Global manager
_manager = None

def get_manager() -> BridgeManager:
    global _manager
    if _manager is None:
        _manager = BridgeManager()
    return _manager


# FastAPI wrapper
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Hermes Bridge v3 - Session Isolation")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

@app.post("/chat")
async def chat(request: ChatRequest):
    manager = get_manager()
    bridge = manager.get_session(request.session_id)
    
    start_time = time.time()
    response = bridge.send(request.message)
    latency = time.time() - start_time
    
    return {
        "response": response,
        "latency_ms": int(latency * 1000),
        "session_id": request.session_id,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/reset")
async def reset(request: ChatRequest):
    manager = get_manager()
    bridge = manager.reset_session(request.session_id)
    return {"status": "reset", "session_id": request.session_id}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    print("🌐 Starting Bridge v3 on port 8083...")
    uvicorn.run(app, host="127.0.0.1", port=8083)
