#!/bin/bash
echo "Starting migration generation script from /app..."
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

# Install/update dependencies (just in case, though should be up to date)
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --user
if [ $? -ne 0 ]; then
    echo "pip install failed!"
    exit 1
fi
echo "Dependencies installed."

# Run Alembic autogenerate
# This assumes Flask-Migrate has configured Alembic correctly to pick up changes from Flask-SQLAlchemy models.
echo "Running Alembic autogenerate..."
flask db migrate -m "create_initial_tables"
# As an alternative, try the direct alembic command if 'flask db migrate' still has issues:
# alembic revision -m "create_initial_tables" --autogenerate

if [ $? -ne 0 ]; then
    echo "Alembic autogenerate command failed!"
    echo "Listing contents of migrations/versions directory:"
    ls -la migrations/versions
    exit 1
fi
echo "Alembic autogenerate command successful."
echo "Listing contents of migrations/versions directory:"
ls -la migrations/versions

echo "Migration generation script completed successfully."
exit 0
