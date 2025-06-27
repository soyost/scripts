#!/bin/bash

NAMESPACE="ibus-cloud-prod"

ALL_SECRETS=$(kubectl get secrets -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')

CLUSTER_SECRETS=$(echo "$ALL_SECRETS" | grep -E '^rabbitmq-(0[12]|[0-9]+)-.*default-user$')

SPRING_SECRETS=$(echo "$ALL_SECRETS" | grep -E '^rabbitmq-spring-cloud-.*default-user$')

SECRET_NAMES=$(echo -e "$CLUSTER_SECRETS\n$SPRING_SECRETS" | sort -u)

if [ -z "$SECRET_NAMES" ]; then
  echo "No matching secrets found"
  exit 1
fi

for SECRET_NAME in $SECRET_NAMES; do
  USERNAME=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.username}' | base64 --decode)
  PASSWORD=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.password}' | base64 --decode)

  echo "==============================="
  echo "Secret:   $SECRET_NAME"
  echo "Username: $USERNAME"
  echo "Password: $PASSWORD"
  echo "==============================="
done

