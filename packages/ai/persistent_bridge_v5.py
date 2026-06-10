#!/usr/bin/env python3
"""
Persistent Hermes Bridge v5
- PTY support for proper TUI rendering
- Extracts LLM response from TUI output
"""

import os
import sys
import json
import time
import re
import select
import pty
import subprocess
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime

class HermesBridge:
    """Hermes session with PTY for TUI support"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.master_fd = None
        self.process = None
        self.ready = False
    
    def start(self):
        """Start Hermes with PTY"""
        # Create PTY
        master, slave = pty.openpty()
        self.master_fd = master
        
        # Start Hermes process with PTY
        cmd = [
            "/home/siddhi/.local/bin/hermes",
            "chat",
            "--model", "kimi-for-coding",
            "--provider", "kimi-coding"
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            preexec_fn=os.setsid
        )
        
        os.close(slave)
        
        # Wait for initialization
        time.sleep(5)
        self.ready = True
        
        # Clear initial output
        self._read_output(timeout=2)
    
    def _read_output(self, timeout: float = 10.0) -> str:
        """Read output from PTY"""
        output = b""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            ready, _, _ = select.select([self.master_fd], [], [], 0.5)
            if ready:
                try:
                    chunk = os.read(self.master_fd, 4096)
                    if chunk:
                        output += chunk
                except OSError:
                    break
            else:
                # No more output
                if output:
                    break
        
        return output.decode('utf-8', errors='replace')
    
    def send(self, message: str) -> str:
        """Send message and get response"""
        if not self.ready or not self.process:
            raise Exception("Bridge not ready")
        
        # Clear any pending output
        self._read_output(timeout=1)
        
        # Send message
        os.write(self.master_fd, (message + "\n").encode())
        
        # Wait for response
        time.sleep(8)  # LLM takes ~6-8s
        
        # Read response
        output = self._read_output(timeout=3)
        
        # Extract actual response
        return self._extract_response(output)
    
    def _extract_response(self, raw_output: str) -> str:
        """Extract LLM response from TUI output"""
        
        # Remove ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', raw_output)
        
        lines = cleaned.split('\n')
        
        # Find user message marker
        found_user_msg = False
        content_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty
            if not stripped:
                continue
            
            # Find user message (● symbol)
            if '●' in stripped:
                found_user_msg = True
                continue
            
            # Skip until we find user message
            if not found_user_msg:
                continue
            
            # Skip TUI artifacts
            if any(x in stripped for x in [
                '⚕', '⏱', '⏲', '❯', '───', '╭', '╰', '┊',
                'kimi-for-coding', 'msg=interrupt', 'Available Tools',
                'Session:', 'Duration:', 'Initializing agent',
                ' pondering', ' reflecting', ' computing',
                'Ctrl+C', '/queue', '/bg', '/steer',
                'Goodbye!', '⚕', '█', '░'
            ]):
                continue
            
            # Skip single chars/digits
            if len(stripped) < 2:
                continue
            
            # Skip border lines
            if stripped.startswith('─') or stripped.startswith('╭') or stripped.startswith('╰'):
                continue
            
            # This is content
            content_lines.append(stripped)
        
        if content_lines:
            # Return longest line (usually the response)
            return max(content_lines, key=len)
        
        return ""
    
    def stop(self):
        """Stop bridge"""
        if self.process:
            self.process.terminate()
            self.process.wait()
        if self.master_fd:
            os.close(self.master_fd)
        self.ready = False


# FastAPI wrapper
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Hermes Bridge v5 - PTY Mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BridgeChatRequest(BaseModel):
    message: str
    session_id: str = "default"

# Global bridge instance
_bridge = None

def get_bridge():
    global _bridge
    if _bridge is None or not _bridge.ready:
        _bridge = HermesBridge("main")
        _bridge.start()
    return _bridge

@app.on_event("startup")
async def startup():
    get_bridge()
    print("🎯 Bridge v5 ready with PTY")

@app.post("/chat")
async def chat(request: BridgeChatRequest):
    bridge = get_bridge()
    
    start_time = time.time()
    response = bridge.send(request.message)
    latency = time.time() - start_time
    
    return {
        "response": response,
        "latency_ms": int(latency * 1000),
        "session_id": request.session_id,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8082)
