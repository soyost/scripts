#!/bin/bash

NAMESPACE="ibus-cloud-prod"

# Find all matching secrets for rabbitmq-01 and rabbitmq-02 with "default-user"
SECRET_NAMES=$(kubectl get secrets -n "$NAMESPACE" | awk '/rabbitmq-[0-9].*default-user/ {print $1}')

# Check if any were found
if [ -z "$SECRET_NAMES" ]; then
  echo "No matching secrets found!"
  exit 1
fi

# Loop through and decode each
for SECRET_NAME in $SECRET_NAMES; do
  USERNAME=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.username}' | base64 --decode)
  PASSWORD=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.password}' | base64 --decode)

  echo "==============================="
  echo "Secret:   $SECRET_NAME"
  echo "Username: $USERNAME"
  echo "Password: $PASSWORD"
  echo "==============================="
done

