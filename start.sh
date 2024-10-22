#!/bin/bash
set -x  # This will print each command as it's executed
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "Script directory: $SCRIPT_DIR"
source "$SCRIPT_DIR/.venv/Scripts/activate"
echo "Virtual environment activated"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
echo "PYTHONPATH set to: $PYTHONPATH"
echo "Installed packages:"
pip list
exec python -m waitress --listen=*:5000 wsgi:app