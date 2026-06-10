#!/bin/bash
cd /home/siddhi/jarvix-backend
python3 -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000)" > /tmp/jarvix.log 2>&1 &
echo $! > /tmp/jarvix.pid
echo "Jarvix backend started on port 8000"
