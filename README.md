# TrekSync — Trekking Management System

TrekSync is a Flask web application for managing trekking trips and bookings. It provides separate workflows for administrators, trek staff, and trekkers, using SQLite for data storage and Jinja templates for the interface.

## Features

### Administrator

- View counts for treks, trekkers, staff, and bookings.
- Create, edit, list, and delete treks.
- Approve staff registrations and enable or disable staff accounts.
- Review trekkers and all bookings.

### Trek staff

- View treks assigned to their account.
- Update trek status and available slots, subject to confirmed booking capacity.
- View participant bookings for assigned treks.

### Trekker

- Browse open treks and search by name, location, and difficulty.
- Book an available slot and view booking history.
- Cancel an active booking.

Booking creation uses a conditional database update to deduct a slot only while the trek is open and has availability. Staff routes also check that the requested trek is assigned to the signed-in staff member.

## Technology

- Python and Flask
- Flask-SQLAlchemy and SQLAlchemy
- SQLite
- Flask-Login and Werkzeug password hashing
- Flask-WTF and WTForms
- Jinja templates and custom CSS

Dependencies are listed in `requirements.txt`.

## Project layout

```text
app.py                 Flask application setup and development entry point
config.py              Flask and SQLite configuration
extensions.py          SQLAlchemy and Flask-Login extensions
seed.py                Rebuilds the database with demo users, treks, and bookings
qa_test_suite.py       Authentication, role access, admin, staff, and booking tests
models/                User, staff profile, trek, and booking models
routes/                Authentication and role-specific route blueprints
forms/                 Authentication, trek, staff update, and search forms
utils/                 Role-based access decorators
templates/             Jinja pages for shared and role-specific views
static/css/            Application styles
instance/trekking.db   SQLite database used by the app
```

## Run locally

Use Python 3.10 or newer.

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS or Linux, activate it with `source .venv/bin/activate`.

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the Flask development server:

   ```bash
   python app.py
   ```

4. Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

The application creates missing database tables during startup. It does not create an administrator account automatically. For a local demo account, use the demo data setup below.

## Demo data

To populate the database with demo accounts, treks, and bookings, run:

```bash
python seed.py
```

**This script drops all existing tables and recreates them. Any data in `instance/trekking.db` will be deleted.**

Demo login credentials:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@test.com` | `admin123` |
| Staff | `staff@test.com` | `staff123` |
| Trekker | `trekker@test.com` | `trekker123` |

The seed also creates a pending staff account (`guide_maya@test.com`) and another trekker (`aria@test.com`); both use the password `staff123` and `trekker123`, respectively.

## Configuration notes

The SQLite database path is configured in `config.py` and points to `instance/trekking.db`. The Flask secret key is currently a development placeholder in that file. Set a private secret key through deployment configuration before exposing the application beyond local development.

## Tests

`qa_test_suite.py` contains a `unittest` suite for authentication, role access, admin and staff workflows, trek discovery, and bookings. Run it from the project directory:

```bash
python qa_test_suite.py
```

The suite resolves the project directory from its own file location and targets the same `instance/trekking.db` configured for the application. It backs up that database, drops and recreates its tables for test data, then restores the backup at teardown. Avoid running the app or changing its database while the suite is running, and keep a separate copy of any important database data before testing.
