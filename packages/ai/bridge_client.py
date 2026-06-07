"""
Hermes Bridge Client - Proper TUI Handling
Uses script command to allocate TTY
"""

import os
import sys
import json
import time
import re
import subprocess
import threading
from typing import Optional

BRIDGE_URL = "http://localhost:8082/chat"

# Try HTTP bridge first, fallback to direct TUI
def call_hermes_bridge(message: str, timeout: int = 15) -> str:
    """
    Call Hermes Bridge via HTTP API
    """
    try:
        import httpx
        
        response = httpx.post(
            BRIDGE_URL,
            json={"message": message},
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            raw = data.get("response", "")
            
            # Clean TUI artifacts
            cleaned = clean_tui_response(raw)
            if cleaned and len(cleaned) > 10:
                return cleaned
                
    except Exception as e:
        print(f"Bridge error: {e}", file=sys.stderr)
    
    return ""


def clean_tui_response(raw: str) -> str:
    """Clean TUI artifacts from bridge response"""
    
    # Split into lines
    lines = raw.split('\n')
    
    # Look for actual content (not TUI)
    content_lines = []
    for line in lines:
        line = line.strip()
        
        # Skip TUI artifacts
        if any(x in line for x in [
            '⚕', '⏱', '⏲', '❯', '───', '╭', '╰',
            'kimi-for-coding', 'msg=interrupt', 'Available Tools',
            'Session:', 'Duration:', 'Initializing agent',
            ' pondering...', ' reflecting...', ' computing...',
            'Ctrl+C', '/queue', '/bg', '/steer'
        ]):
            continue
        
        # Skip empty lines
        if not line:
            continue
            
        # Skip single digits
        if line in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
            continue
            
        # Skip ANSI sequences
        line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line)
        
        # Keep lines that look like actual content
        if len(line) > 20 and not line.startswith('[') and not line.startswith('{'):
            content_lines.append(line)
    
    if content_lines:
        # Return longest content line (usually the actual response)
        return max(content_lines, key=len)
    
    return ""


# Test
if __name__ == "__main__":
    result = call_hermes_bridge("Say 'Jarvix is ready, sir.'")
    print(f"Response: {repr(result)}")
