#!/bin/bash
# Helper script to run scripts with virtual environment activated

# Activate virtual environment
source venv/bin/activate

# Run the command passed as arguments
"$@"

