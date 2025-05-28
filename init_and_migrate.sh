#!/bin/bash
echo "Starting migration init and execution script from /app..."
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

# Install/update dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --user
if [ $? -ne 0 ]; then
    echo "pip install failed!"
    exit 1
fi
echo "Dependencies installed."

# Remove existing migrations directory if it exists, to ensure a clean init
if [ -d "migrations" ]; then
    echo "Removing existing migrations directory..."
    rm -rf migrations
    if [ $? -ne 0 ]; then
        echo "Failed to remove migrations directory!"
        # Continue anyway, flask db init might handle it
    fi
fi

# Initialize the migrations directory
echo "Running flask db init..."
flask db init
if [ $? -ne 0 ]; then
    echo "flask db init failed!"
    # Attempt to list contents even if init fails, for diagnostics
    echo "Listing contents of current directory (should be climbing_app_backend):"
    ls -la
    echo "Listing contents of migrations directory if it exists:"
    ls -la migrations
    exit 1
fi
echo "flask db init successful."
echo "Listing contents of migrations directory:"
ls -la migrations

# Run database migration for user authentication
echo "Running flask db migrate for auth..."
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
