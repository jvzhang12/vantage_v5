#!/bin/sh
set -eu

DATA_ROOT="${VANTAGE_V5_REPO_ROOT:-/data}"
ACTIVE_WORKSPACE="${VANTAGE_V5_ACTIVE_WORKSPACE:-v5-milestone-1}"

for dir in artifacts concepts memories memory_trace state traces workspaces; do
  mkdir -p "${DATA_ROOT}/${dir}"
done

if [ ! -f "${DATA_ROOT}/workspaces/${ACTIVE_WORKSPACE}.md" ]; then
  cat > "${DATA_ROOT}/workspaces/${ACTIVE_WORKSPACE}.md" <<EOF
# Vantage Workspace

Use this whiteboard for shared drafts.
EOF
fi

if [ ! -f "${DATA_ROOT}/state/active_workspace.json" ]; then
  cat > "${DATA_ROOT}/state/active_workspace.json" <<EOF
{
  "active_workspace_id": "${ACTIVE_WORKSPACE}",
  "active_workspace_path": "workspaces/${ACTIVE_WORKSPACE}.md",
  "status": "active"
}
EOF
fi

exec "$@"
