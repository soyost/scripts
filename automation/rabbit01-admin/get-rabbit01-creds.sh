#!/bin/bash

NAMESPACE="ibus-cloud-prod"

# Auto-detect the secret name
SECRET_NAME=$(kubectl get secrets -n "$NAMESPACE" | awk '/rabbitmq-01.*default-user/ {print $1}')

# Check if we found it
if [ -z "$SECRET_NAME" ]; then
  echo "Secret not found!"
  exit 1
fi

# Decode and print
USERNAME=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.username}' | base64 --decode)
PASSWORD=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.password}' | base64 --decode)

echo "Secret: $SECRET_NAME"
echo "Username: $USERNAME"
echo "Password: $PASSWORD"

