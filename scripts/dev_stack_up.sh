#!/bin/bash
# Bring up the local IBA dev stack after a host/WSL restart killed the
# non-docker processes (iba-web, local-proxy, iba-workflows api+worker,
# BPOM tunnel) and the manually-run seeknal-worker-m9 container.
#
# Does NOT touch application code in iba/ or seeknal/ — only starts existing
# entrypoints. Docker infra (postgres/redis/keycloak/...) is assumed already
# up via `cd iba && make infra-up`.
#
# Usage: bash scripts/dev_stack_up.sh

set -euo pipefail

IBA_ROOT="/home/mta/projects/seeknal_audit/iba"
WORKFLOWS_ROOT="$IBA_ROOT/workflows/iba-workflows"
AUDIT_ROOT="/home/mta/projects/seeknal_audit"
BPOM_ROOT="/home/mta/projects/seeknal_audit/seeknal-bpom-neo"
LOG_DIR="/tmp/iba-logs"
mkdir -p "$LOG_DIR"

echo "== 1/6 Docker infra check =="
docker ps --format '{{.Names}}' | grep -q '^iba-postgres$' || { echo "iba-postgres not up — run 'cd $IBA_ROOT && make infra-up' first"; exit 1; }
echo "infra OK"

echo "== 2/6 iba-web (next dev :6300) =="
# package.json's "dev" script is bare "next dev" (no -p) — the port comes
# from the PORT env var, per iba/Procfile's "web:" line.
if ! ss -tln | grep -q ':6300 '; then
  (cd "$IBA_ROOT/apps/iba-web" && PORT=6300 AUTH_URL=http://localhost:6443 nohup pnpm run dev > "$LOG_DIR/iba-web.log" 2>&1 &)
  echo "started, logs: $LOG_DIR/iba-web.log"
else
  echo "already up"
fi

echo "== 3/6 local-proxy (:6443) =="
if ! ss -tln | grep -q ':6443 '; then
  (cd "$AUDIT_ROOT" && nohup python3 "docs/testing/how to testing/local-proxy.py" > "$LOG_DIR/local-proxy.log" 2>&1 &)
  echo "started, logs: $LOG_DIR/local-proxy.log"
else
  echo "already up"
fi

echo "== 4/6 iba-workflows API (:6835) + worker =="
# iba-workflows/.env is written for full docker-compose (redis/temporal/
# postgres/iba-service all as docker-internal hostnames). This hybrid setup
# runs iba-workflows on the HOST against dockerized infra, so every
# docker-hostname default must be overridden to the host-mapped port.
# Also: -m scripts.start_api (module form), not "python scripts/start_api.py"
# (bare-script form) -- the latter breaks `from app... import` with
# ModuleNotFoundError since scripts/ isn't the package root.
WF_ENV=(
  TEMPORAL_HOST=localhost:6723
  REDIS_URL=redis://localhost:6637
  WORKFLOWS_DATABASE_URL=postgresql://postgres:postgres@localhost:6543/iba_workflows
  KEYMETRICS_DATABASE_URL=postgresql://postgres:postgres@localhost:6543/iba_workflows
  INTERNAL_HMAC_SECRET=iba-dev-hmac-secret-change-in-prod
  IBA_SERVICE_URL=http://localhost:6800/services/iba
  API_PORT=6835
)
if ! ss -tln | grep -q ':6835 '; then
  (cd "$WORKFLOWS_ROOT" && env "${WF_ENV[@]}" nohup uv run python -m scripts.start_api > "$LOG_DIR/workflows-api.log" 2>&1 &)
  echo "api started, logs: $LOG_DIR/workflows-api.log"
else
  echo "api already up"
fi
if ! pgrep -f "scripts.start_worker" > /dev/null; then
  (cd "$WORKFLOWS_ROOT" && env "${WF_ENV[@]}" nohup uv run python -m scripts.start_worker > "$LOG_DIR/workflows-worker.log" 2>&1 &)
  echo "worker started, logs: $LOG_DIR/workflows-worker.log"
else
  echo "worker already up"
fi

echo "== 5/6 BPOM SSH tunnel (:5533) =="
if ! ss -tln | grep -q ':5533 '; then
  (cd "$BPOM_ROOT" && nohup bash scripts/start_tunnel.sh > "$LOG_DIR/bpom-tunnel.log" 2>&1 &)
  echo "started, logs: $LOG_DIR/bpom-tunnel.log"
else
  echo "already up"
fi

echo "== 6/6 seeknal-worker-m9 container =="
if [ "$(docker inspect -f '{{.State.Running}}' seeknal-worker-m9 2>/dev/null)" != "true" ]; then
  docker start seeknal-worker-m9
else
  echo "already running"
fi

echo ""
echo "Waiting 8s for processes to bind ports..."
sleep 8

echo ""
echo "== Health check =="
for port_desc in "6300:iba-web" "6443:local-proxy" "6800:iba-service(docker)" "6835:workflows-api" "5533:bpom-tunnel"; do
  port="${port_desc%%:*}"; desc="${port_desc##*:}"
  if ss -tln | grep -q ":${port} "; then
    echo "  [OK]   $desc :$port"
  else
    echo "  [DOWN] $desc :$port -- check $LOG_DIR/*.log"
  fi
done
docker inspect -f '  [{{.State.Status}}] seeknal-worker-m9' seeknal-worker-m9 2>/dev/null || echo "  [MISSING] seeknal-worker-m9"
