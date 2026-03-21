#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$ROOT_DIR/data"

mkdir -p "$DATA_DIR"

echo "[INFO] Resetting JSON data files in $DATA_DIR"

for f in \
  calendar_blocks.json \
  client_notes.json \
  clients.json \
  contracts.json \
  crm_interactions.json \
  drp_history.json \
  expenses.json \
  invoices.json \
  quotes.json \
  scoped_projects.json \
  sdlc_templates.json \
  timer_sessions.json \
  workhours.json
  do
  printf '[]\n' > "$DATA_DIR/$f"
done

cat > "$DATA_DIR/settings.json" << 'EOF'
{
  "name": "Your Name",
  "business": "Freelancer",
  "currency": "USD",
  "currency_symbol": "$",
  "default_rate": 50.0,
  "working_hours_per_day": 8.0,
  "late_fee_rate": 1.5
}
EOF

echo "[OK] JSON data reset complete."
echo "[INFO] On next app launch, built-in SDLC templates will be auto-seeded."
