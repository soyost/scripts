#!/usr/bin/env bash

set -euo pipefail

WARN_DAYS=10

HOSTS=(
  "isksophex01.studios.t-mobile.net:443"
  "faksophex01.studios.t-mobile.net:443"
  "faksophex02.studios.t-mobile.net:443"
)

for entry in "${HOSTS[@]}"; do
  HOST="${entry%%:*}"
  PORT="${entry##*:}"

  ENDDATE=$(
    echo | openssl s_client -servername "$HOST" -connect "$HOST:$PORT" 2>/dev/null \
      | openssl x509 -noout -enddate 2>/dev/null \
      | cut -d= -f2
  )

  if [[ -z "$ENDDATE" ]]; then
    printf "%-35s %-8s %-30s %-10s\n" "$HOST:$PORT" "ERROR" "no cert" "-"
    continue
  fi

  EXPIRY_EPOCH=$(date -d "$ENDDATE" +%s)
  NOW_EPOCH=$(date +%s)
  DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

  STATUS="OK"
  if (( DAYS_LEFT < 0 )); then
    STATUS="EXPIRED"
  elif (( DAYS_LEFT < WARN_DAYS )); then
    STATUS="WARN"
  fi

  printf "%-35s %-8s %-30s %-10s\n" "$HOST:$PORT" "$STATUS" "$ENDDATE" "$DAYS_LEFT"
done