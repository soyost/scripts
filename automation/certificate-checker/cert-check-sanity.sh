#!/usr/bin/env bash

set -euo pipefail

WARN_DAYS=10

HOSTS=(
  "isksophex01.studios.t-mobile.net:443"
  "faksophex01.studios.t-mobile.net:443"
  "faksophex02.studios.t-mobile.net:443"
  "google.com:443"
)

printf "%-40s %-12s %-8s %-25s %-30s %-25s\n" \
  "HOST:PORT" "STATUS" "DAYS" "EXPIRES" "ISSUER" "VERIFY"

for entry in "${HOSTS[@]}"; do
  HOST="${entry%%:*}"
  PORT="${entry##*:}"

  CERT_DATA=$(echo | openssl s_client -servername "$HOST" -connect "$HOST:$PORT" 2>/dev/null || true)

  ENDDATE=$(printf '%s\n' "$CERT_DATA" | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || true)
  SUBJECT=$(printf '%s\n' "$CERT_DATA" | openssl x509 -noout -subject 2>/dev/null | sed 's/^subject=//' || true)
  ISSUER=$(printf '%s\n' "$CERT_DATA" | openssl x509 -noout -issuer 2>/dev/null | sed 's/^issuer=//' || true)
  VERIFY=$(printf '%s\n' "$CERT_DATA" | awk -F': ' '/Verify return code/ {print $2}' | tail -n1)

  if [[ -z "$ENDDATE" ]]; then
    printf "%-40s %-12s %-8s %-25s %-30s %-25s\n" \
      "$HOST:$PORT" "ERROR" "-" "-" "-" "no cert"
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

  if [[ "$SUBJECT" == "$ISSUER" ]]; then
    STATUS="SELF-SIGNED"
  elif [[ "${VERIFY:-}" != "0 (ok)" && "$STATUS" == "OK" ]]; then
    STATUS="VERIFY-FAIL"
  fi

  SHORT_ISSUER=$(printf '%s' "$ISSUER" | sed 's/.*CN[[:space:]]*=[[:space:]]*//; s/,.*//')
  [[ -z "$SHORT_ISSUER" ]] && SHORT_ISSUER="$ISSUER"

  printf "%-40s %-12s %-8s %-25.25s %-30.30s %-25.25s\n" \
    "$HOST:$PORT" "$STATUS" "$DAYS_LEFT" "$ENDDATE" "$SHORT_ISSUER" "${VERIFY:-unknown}"
done