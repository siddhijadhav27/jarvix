#!/usr/bin/env python3
import sys
import os

# Ensure we're using the local packages
sys.path.insert(0, '/home/siddhi/jarvix-backend/packages')

# Clear any cached modules
modules_to_clear = [key for key in sys.modules.keys() if 'ai' in key or 'personality' in key]
for mod in modules_to_clear:
    del sys.modules[mod]

import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
