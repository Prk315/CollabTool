# Purpose
This project is created for the course database and information systems. As seen in lecture 1 we are primarily using python combined with flask and postgresql. We have chosen to opt for using external templates for the calendar creation and such, since the frontend of this application isnt truly relevent to the course.

# Creators
Bastian Rønfeldt Thomsen - prk315

Andreas Christian Kærlev - bzd796

Andreas Lydum Larsen - bfh549

# Student Collaboration Tool
A Flask-based web application that helps student groups find optimal meeting times and manage project deadlines based on shared availability. Calendar data can be imported via `.ics` files.

---

## Features

- User registration and group membership
- Project creation with deadlines and effort estimation
- Upload `.ics` calendar files to generate availability
- Detect shared free time across group members
- Alert when insufficient time exists to meet project goals

---

## Getting Started
## Notice windows Users:
We recommend the use of Powershell for installation
### Developer Setup Instructions

Below are the complete steps to set up and run the application:

#### Prerequisites
- Python 3.10 or higher
- PostgreSQL (version 13 or higher recommended)
- Git

#### Installation


1. **Clone the repository** (if you haven't already)
   ```bash
   git clone https://github.com/Prk315/CollabTool.git
   cd CollabTool
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   # NOTE: Might need to run
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   # to allow it to run in powershell

   # Linux/macOS
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Setup**
   
   The application uses PostgreSQL. You'll need to:
   
   a. **Run the migration script**
   ```bash
   # Windows
   cd db\migrations
   .\fixed_migrate.ps1
   
   # When prompted, enter your PostgreSQL password for the 'postgres' user
   # This script will:
   # - Create the 'collabtool' database if it doesn't exist
   # - Apply all migrations in the correct order
   # - Track applied migrations

   # NOTICE: The database collation version might mismatch with the users version. run REFRESH COLLATION VERSION if needed
   ```

   b. **Alternative manual setup** (if the script doesn't work)
   ```bash
   # Create database
   psql -U postgres -c "CREATE DATABASE collabtool;"
   
   # Apply migrations manually
   cd db/migrations
   psql -U postgres -d collabtool -f 001_initial_schema.sql
   psql -U postgres -d collabtool -f 002_calendar_id.sql
   psql -U postgres -d collabtool -f 003_work_sessions.sql
   # Continue with any additional migration files
   ```

5. **Run the application**
   ```bash
   # Return to the project root directory if needed
   cd ../..
   
   # Run the Flask application
   flask --app backend.app run
   
   # For development mode with auto-reload
   flask --app backend.app run --debug
   
   #NOTICE:
   # A .env file is required to access the database.
   # Please refer to the .env file example in the repository
   # If you are unsure how to add one
   ```

6. **Access the application**
   
   Open your web browser and navigate to: http://127.0.0.1:5000/

# For my fellow students

flask --app backend.app run         

is the command to run the application and please dont mess with the internal psql postres.

#### Troubleshooting

- **Database Connection Issues**: Make sure PostgreSQL is running and that the connection parameters in the code match your PostgreSQL setup
- **Migration Errors**: If you encounter issues with migrations, you can manually apply SQL files in the correct order
- **Import Errors**: Ensure you're running the application from the project root directory and that your virtual environment is activated

### Notes for Developers

- The application uses Flask's development server by default. For production, consider using a proper WSGI server like Gunicorn
- Calendar data (.ics files) can be imported through the appropriate UI in the application
- User authentication is simple and not production-ready - enhance security before deploying to production

### ER Diagram

![ER Diagram group](https://github.com/user-attachments/assets/c621da30-57ea-4bd4-829e-961760dc2ec7)
