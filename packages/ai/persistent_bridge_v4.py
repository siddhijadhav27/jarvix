#!/usr/bin/env python3
"""
Persistent Hermes Bridge v4
- Pre-warmed session pool for <4s response time
- Session isolation per user
- JSON corruption fix
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
from typing import Dict, Any, Optional, List
from datetime import datetime

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
        
        # Wait for response with adaptive timeout
        start_time = time.time()
        timeout = 10  # Max 10s (response usually ready at ~6s)
        check_interval = 0.5
        
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            
            with self.buffer_lock:
                current_len = len(self.output_buffer)
            
            if current_len > start_len:
                # Got output, check if we have a real response
                with self.buffer_lock:
                    new_lines = self.output_buffer[start_len:]
                    new_output = "".join(new_lines)
                
                response = self._extract_response(new_output)
                
                # If response has real content (not UI), return it
                if (len(response) > 30 and 
                    not response.startswith('│') and
                    not response.startswith('⚕') and
                    not response.startswith('●') and
                    not response.startswith('❯') and
                    not response.startswith('─') and
                    'kimi-for-coding' not in response and
                    'msg=interrupt' not in response):
                    return response
        
        # Timeout — return best effort
        with self.buffer_lock:
            new_lines = self.output_buffer[start_len:]
            new_output = "".join(new_lines)
        
        return self._extract_response(new_output)
    
    def _extract_response(self, raw_output: str) -> str:
        """Extract clean response with JSON safety"""
        
        # Remove ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', raw_output)
        
        # Strategy 1: Find and fix JSON
        json_result = self._extract_json_safe(cleaned)
        if json_result:
            return json_result
        
        # Strategy 2: Look for content keywords (Bitcoin, ETH, etc.)
        content_keywords = [
            'Bitcoin', 'Ethereum', 'ETH', 'BTC', 'SOL', 'decentralized',
            'portfolio', 'price', 'buy', 'sell', 'intent', 'asset'
        ]
        
        lines = cleaned.split('\n')
        for line in lines:
            stripped = line.strip()
            if any(kw in stripped for kw in content_keywords):
                if len(stripped) > 30 and not any(x in stripped for x in [
                    'kimi-for-coding', 'msg=interrupt', '⚕', '⏱', '⏲',
                    '───', '❯', 'Available Tools', 'Available Skills'
                ]):
                    return stripped
        
        # Strategy 3: Find longest content line
        content_lines = []
        for line in lines:
            stripped = line.strip()
            if (len(stripped) > 20 and 
                not any(x in stripped for x in [
                    'kimi-for-coding', 'msg=interrupt', '⚕', '⏱', '⏲',
                    '───', '❯', 'Available Tools', 'Available Skills',
                    'Session:', 'Duration:', 'Messages:', 'Resume',
                    'Initializing agent...'
                ])):
                content_lines.append(stripped)
        
        if content_lines:
            return max(content_lines, key=len)
        
        return cleaned.strip()[:500]
    
    def _extract_json_safe(self, text: str) -> Optional[str]:
        """Safely extract JSON with corruption handling"""
        
        start = text.find('{')
        end = text.rfind('}')
        
        if start == -1 or end == -1 or end < start:
            return None
        
        json_str = text[start:end+1]
        json_str = json_str.replace('\n', ' ')
        json_str = json_str.replace('\r', '')
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        
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


class BridgeManager:
    """Manages pre-warmed bridge sessions"""
    
    def __init__(self, pool_size: int = 5):
        self.sessions: Dict[str, HermesBridge] = {}
        self.warm_pool: List[HermesBridge] = []
        self.pool_size = pool_size
        self.lock = threading.Lock()
    
    def initialize(self):
        """Pre-warm session pool at startup"""
        print(f"🚀 Pre-warming {self.pool_size} bridge sessions...")
        
        for i in range(self.pool_size):
            bridge = HermesBridge(session_id=f"pool_{i}")
            bridge.start()
            self.warm_pool.append(bridge)
            print(f"  ✅ Pool session {i+1}/{self.pool_size} ready")
        
        print(f"🎯 Pool ready: {self.pool_size} sessions warm")
    
    def get_session(self, session_id: str) -> HermesBridge:
        """Get session - from existing, pool, or cold start"""
        with self.lock:
            # Return existing session
            if session_id in self.sessions:
                return self.sessions[session_id]
            
            # Grab from warm pool
            if self.warm_pool:
                bridge = self.warm_pool.pop(0)
                bridge.session_id = session_id
                self.sessions[session_id] = bridge
                
                # Refill pool in background
                threading.Thread(target=self._refill_pool, daemon=True).start()
                
                return bridge
            
            # Cold start (rare)
            print(f"⚠️ Pool empty, cold starting for {session_id}")
            bridge = HermesBridge(session_id=session_id)
            bridge.start()
            self.sessions[session_id] = bridge
            return bridge
    
    def _refill_pool(self):
        """Background pool refill"""
        while len(self.warm_pool) < self.pool_size:
            bridge = HermesBridge(session_id=f"pool_{len(self.warm_pool)}")
            bridge.start()
            with self.lock:
                self.warm_pool.append(bridge)
    
    def destroy_session(self, session_id: str):
        """Destroy a session"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].stop()
                del self.sessions[session_id]
    
    def reset_session(self, session_id: str) -> HermesBridge:
        """Reset session"""
        self.destroy_session(session_id)
        return self.get_session(session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return {
            "active_sessions": len(self.sessions),
            "warm_pool": len(self.warm_pool),
            "pool_size": self.pool_size
        }


# Global manager
_manager = None

def get_manager() -> BridgeManager:
    global _manager
    if _manager is None:
        _manager = BridgeManager(pool_size=5)
    return _manager


# FastAPI wrapper
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Hermes Bridge v4 - Pre-warmed Pool")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

@app.on_event("startup")
async def startup():
    manager = get_manager()
    manager.initialize()
    print("🎯 Jarvix Bridge ready")

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

@app.get("/health")
async def health():
    manager = get_manager()
    stats = manager.get_stats()
    return {
        "status": "healthy",
        "stats": stats
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8083)
