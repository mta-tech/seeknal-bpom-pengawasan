#!/bin/bash
# SSH tunnel: forward localhost:5533 to remote postgres:5433
# Keep this terminal open while running tests or the agent.
# See docs/testing_guide.md for full setup instructions.

SSH_PASS="CBN25*pom"
SERVER_IP="10.59.2.29"
SSH_USER="cbnpom"
LOCAL_PORT=5533
REMOTE_PORT=5433

echo "Starting SSH tunnel: localhost:${LOCAL_PORT} -> ${SERVER_IP}:${REMOTE_PORT}"
echo "Press Ctrl+C to stop."

sshpass -p "$SSH_PASS" ssh \
  -L "${LOCAL_PORT}:localhost:${REMOTE_PORT}" \
  -o ServerAliveInterval=60 \
  -o StrictHostKeyChecking=no \
  -N \
  "${SSH_USER}@${SERVER_IP}"
