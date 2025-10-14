#!/bin/bash

# --- Configuration ---
PRIVATE_KEY=PRIVATE_KEY=<location of public key>

# --- Input validation ---
if [ -z "$1" ]; then
  echo "Usage: $0 '<OCI SSH command with <privateKey> placeholders>'"
  exit 1
fi

# --- Replace <privateKey> placeholders ---
COMMAND="${1//<privateKey>/$PRIVATE_KEY}"

# --- Inject missing key algorithm options ---
COMMAND=$(echo "$COMMAND" | sed \
  -E 's#ssh -i ([^ ]+) #ssh -i \1 -o HostKeyAlgorithms=+ecdsa-sha2-nistp256,ssh-ed25519 -o PubkeyAcceptedKeyTypes=+ecdsa-sha2-nistp256,ssh-ed25519 #')

# --- Show and run ---
echo "Running SSH command:"
echo "$COMMAND"
echo

eval "$COMMAND"
