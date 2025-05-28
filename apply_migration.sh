#!/bin/bash
echo "Starting database upgrade script from /app..."
echo "Current directory: $(pwd)"

# Change to the project directory
echo "Changing directory to climbing_app_backend..."
cd climbing_app_backend
if [ $? -ne 0 ]; then
    echo "Failed to change directory to climbing_app_backend!"
    exit 1
fi
echo "Successfully changed directory. New current directory: $(pwd)"

# Ensure FLASK_APP is set
export FLASK_APP=run.py
echo "FLASK_APP set to: $FLASK_APP"

# Add .local/bin to PATH
export PATH="$HOME/.local/bin:$PATH"
echo "PATH set to: $PATH"

# Install/update dependencies (just in case)
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --user
if [ $? -ne 0 ]; then
    echo "pip install failed!"
    exit 1
fi
echo "Dependencies installed."

# Run flask db upgrade
echo "Running flask db upgrade..."
flask db upgrade
if [ $? -ne 0 ]; then
    echo "flask db upgrade failed!"
    # Attempt to get more info if possible
    echo "Attempting to check current revision..."
    flask db current
    exit 1
fi
echo "flask db upgrade successful."
echo "Verifying current revision (should be 0001):"
flask db current

echo "Database upgrade script completed successfully."
exit 0
