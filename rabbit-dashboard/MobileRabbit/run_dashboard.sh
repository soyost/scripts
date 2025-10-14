#!/bin/bash
set -e  # Exit if any step fails

# Step 1: Create a virtual environment if it doesn't exist yet
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Step 2: Activate the virtual environment
source venv/bin/activate

pip install --upgrade pip
pip install requests pandas dash plotly

if [ $# -lt 1 ]; then
  echo "Usage: $0 <python_script.py> [script_args]"
  exit 1
fi

PY_SCRIPT="$1"
shift  # remove the first argument (the script name), so "$@" is the rest

# Step 5: Run the chosen script with any extra arguments
python3 "$PY_SCRIPT" "$@"
