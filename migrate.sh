#!/bin/bash
echo "Starting migration script from /app..."
echo "Current directory: $(pwd)"

# Change to the project directory
echo "Changing directory to climbing_app_backend..."
cd climbing_app_backend
if [ $? -ne 0 ]; then
    echo "Failed to change directory to climbing_app_backend!"
    echo "Listing contents of /app:"
    ls -la /app
    echo "Listing contents of /app/climbing_app_backend if it exists:"
    ls -la /app/climbing_app_backend
    exit 1
fi
echo "Successfully changed directory. New current directory: $(pwd)"

# Ensure FLASK_APP is set for subsequent flask commands
export FLASK_APP=run.py
echo "FLASK_APP set to: $FLASK_APP"

# Add .local/bin to PATH if flask was installed there by pip
export PATH="$HOME/.local/bin:$PATH"
echo "PATH set to: $PATH"

# Install/update dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --user
if [ $? -ne 0 ]; then
    echo "pip install failed!"
    exit 1
fi
echo "Dependencies installed."

# Check if migrations directory exists, if not, run flask db init
if [ ! -d "migrations" ]; then
    echo "Migrations directory not found. Initializing..."
    flask db init
    if [ $? -ne 0 ]; then
        echo "flask db init failed!"
        exit 1
    fi
    echo "Migrations directory initialized."
else
    echo "Migrations directory found."
fi

# Run database migration
echo "Running flask db migrate..."
flask db migrate -m "Implement user authentication with Flask-Login"
if [ $? -ne 0 ]; then
    echo "flask db migrate failed!"
    exit 1
fi
echo "flask db migrate successful."

# Apply the migration
echo "Running flask db upgrade..."
flask db upgrade
if [ $? -ne 0 ]; then
    echo "flask db upgrade failed!"
    exit 1
fi
echo "flask db upgrade successful."

echo "Migration script completed successfully."
exit 0
