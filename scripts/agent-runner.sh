#!/usr/bin/env bash
set -euo pipefail

# Simple agent runner for the example agents. Reads JSON from stdin and emits JSON to stdout.
# Expects input JSON like: {"task":"run-bmad","args":["--in","file.lat"],"target_branch":"feat/auto"}

read -r INPUT_JSON || true

if [ -z "$INPUT_JSON" ]; then
  echo '{"status":"error","message":"no input provided","logs":[]}'
  exit 1
fi

# parse with jq if available, otherwise use simple parsing
if command -v jq >/dev/null 2>&1; then
  TASK=$(echo "$INPUT_JSON" | jq -r '.task // empty')
  ARGS=$(echo "$INPUT_JSON" | jq -r '.args // empty')
  TARGET_BRANCH=$(echo "$INPUT_JSON" | jq -r '.target_branch // empty')
else
  TASK=$(echo "$INPUT_JSON" | grep -oP '"task"\s*:\s*"\K[^"]+' || true)
  ARGS=""
  TARGET_BRANCH=$(echo "$INPUT_JSON" | grep -oP '"target_branch"\s*:\s*"\K[^"]+' || true)
fi

LOGS=()

if [ "$TASK" = "run-bmad" ]; then
  if [ -z "${BMAD_CLI_PATH:-}" ]; then
    LOGS+=("BMAD_CLI_PATH not set; cannot run BMAD CLI")
    echo "{\"status\":\"error\",\"message\":\"BMAD_CLI_PATH not configured\",\"logs\":[\"${LOGS[*]}\"]}"
    exit 0
  fi
  # run BMAD CLI with args (naively split by space)
  LOGS+=("Running BMAD CLI: $BMAD_CLI_PATH $ARGS")
  set +e
  OUTPUT=$($BMAD_CLI_PATH $ARGS 2>&1)
  RET=$?
  set -e
  LOGS+=("$OUTPUT")
  if [ $RET -ne 0 ]; then
    echo "{\"status\":\"error\",\"message\":\"BMAD CLI failed\",\"logs\": [\"${LOGS[*]}\"]}"
    exit 0
  fi
  echo "{\"status\":\"ok\",\"message\":\"BMAD run completed\",\"logs\": [\"${LOGS[*]}\"]}"
  exit 0
fi

# default behavior: echo the received task
LOGS+=("Received task: $TASK")
if [ -n "$TARGET_BRANCH" ]; then
  LOGS+=("Target branch: $TARGET_BRANCH")
fi

echo "{\"status\":\"ok\",\"message\":\"task handled\",\"logs\": [\"${LOGS[*]}\"]}"