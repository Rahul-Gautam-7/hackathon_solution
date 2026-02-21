# FleetFlow — Modular Fleet & Logistics Management System

A full-stack web application built with **Flask + MySQL** that replaces manual logbooks with an intelligent, role-based fleet management hub.

---

## Prerequisites

- Python 3.8+
- XAMPP (MySQL running locally)
- pip

---

##  Steps are as follows:

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up the Database (XAMPP)

1. Start **Apache** and **MySQL** from the XAMPP Control Panel
2. Open **http://localhost/phpmyadmin** in your browser
3. Click **New** → create a database named `fleetflow_db`
4. Select `fleetflow_db` → click the **Import** tab
5. Choose `schema.sql` → click **Go**

### 3. Configure Database Connection

Edit `app.py` and update the DB config (XAMPP defaults shown):
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'fleetflow_db',
    'user': 'root',
    'password': ''   # Leave blank for XAMPP default
}
```

### 4. Run the Application
```bash
python app.py
```

Open your browser: **http://localhost:5000**

---

##  Authentication

### Demo Login Accounts
All demo accounts use password: `admin123`

| Email | Role | Access Level |
|---|---|---|
| admin@fleetflow.com | Manager | Full access to all modules |
| dispatch@fleetflow.com | Dispatcher | Create/edit/delete Trips only |
| safety@fleetflow.com | Safety Officer | Create/edit/delete Drivers only |
| finance@fleetflow.com | Financial Analyst | Create/edit/delete Maintenance & Expenses |

### Register New Account
Visit **http://localhost:5000/register** to create a new account. Select your role from the visual role picker during registration.

---

##  Role-Based Access Control (RBAC)

Each role has write access to specific modules. All other modules are read-only for that role.

| Module | Manager | Dispatcher | Safety Officer | Financial Analyst |
|---|---|---|---|---|
| Dashboard |  Full |  View |  View |  View |
| Vehicle Registry |  Full |  View |  View |  View |
| Trip Dispatcher |  Full |  Full |  View |  View |
| Driver Profiles |  Full |  View |  Full |  View |
| Maintenance Logs |  Full |  View |  View |  Full |
| Fuel & Expenses |  Full |  View |  View |  Full |
| Analytics |  View |  View |  View |  View |

- Read-only users see a **👁 Read Only** badge instead of action buttons
- Any direct POST attempt to a restricted route returns an access denied flash message
- The user's role is always visible as a **color-coded badge** in the sidebar

---

##  Project Structure

```
fleetflow/
├── app.py                  # Flask routes, business logic, RBAC decorators
├── schema.sql              # MySQL schema + seed data (4 users, 8 vehicles, 6 drivers)
├── requirements.txt        # Python dependencies
├── README.md               
└── templates/
    ├── base.html           # Shared layout: sidebar, topbar, dark theme CSS
    ├── login.html          # Animated login page with floating KPI cards
    ├── register.html       # Registration page with role picker
    ├── dashboard.html      # Command Center — KPIs, recent trips, alerts
    ├── vehicles.html       # Vehicle Registry — CRUD, status toggles
    ├── trips.html          # Trip Dispatcher — create, edit (Draft), dispatch, complete
    ├── drivers.html        # Driver Profiles — CRUD, license expiry tracking
    ├── maintenance.html    # Maintenance Logs — service records, completion
    ├── expenses.html       # Fuel & Expense Logs — per-vehicle fuel tracking
    └── analytics.html      # Charts & Reports — efficiency, costs, driver leaderboard
```

---

##  Module Overview

###  Vehicle Registry (`/vehicles`)
- Add, edit, and delete vehicles with type, license plate, max cargo capacity, and odometer
- Toggle vehicles **Out of Service** / **Available**
- Vehicle status is automatically managed by the system:
  - Set to **On Trip** when a trip is dispatched
  - Set to **In Shop** when a maintenance log is created
  - Returned to **Available** when a trip completes or maintenance is marked done

###  Trip Dispatcher (`/trips`)
- Full trip lifecycle: **Draft → Dispatched → Completed / Cancelled**
- **Draft trips are fully editable** — vehicle, driver, route, cargo can all be changed
- Cargo weight validation blocks dispatch if weight exceeds the selected vehicle's max capacity
- Driver dropdown shows all non-suspended drivers with warnings for expired licenses or Off Duty status
- Completing a trip records final odometer, increments driver's trip count, and frees the vehicle

###  Driver Profiles (`/drivers`)
- Card-based layout showing safety score, trips completed, license number, expiry date and status
- License expiry color coding:
  -  **Red** — already expired 
  -  **Yellow** — expires within 30 days 
  -  **Green** — valid 
- Status management: On Duty / Off Duty / Suspended

###  Maintenance Logs (`/maintenance`)
- Log service records against any vehicle
- Creating a maintenance log automatically sets the vehicle status to **In Shop**
- Marking maintenance **Done** returns the vehicle to **Available**

###  Fuel & Expenses (`/expenses`)
- Log fuel entries per vehicle with liters, cost, odometer reading, and date
- **Linked Trip dropdown is filtered** — only shows completed trips that belong to the selected vehicle
- Cost per liter is auto-calculated in the table view

###  Analytics (`/analytics`)
- **Fuel Efficiency Table** — km/L per vehicle using odometer data with intelligent fallback calculation
- **Cost Breakdown** — fuel cost vs maintenance cost per vehicle
- **Trip Status Chart** — doughnut chart of Draft / Dispatched / Completed / Cancelled
- **Monthly Fuel Spend** — bar chart of fuel costs over the months
- **Driver Leaderboard** — ranked by trips completed with safety scores

---

##  Validation Rules

| Rule | Behaviour |
|---|---|
| Cargo overload | Trip cannot be dispatched if cargo weight exceeds vehicle max capacity |
| Expired license | Driver shown with warning; can still be assigned but dispatcher is alerted |
| Maintenance in progress | Vehicle removed from available pool; cannot be assigned to new trips |
| Trip completion | Vehicle freed, driver trips_completed counter incremented |
| Draft editing | Only Draft-status trips can be edited; Dispatched/Completed/Cancelled are locked |
| Role write guard | All write routes check role server-side via `@write_required('module')` decorator |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.0.0, Python 3.8+ |
| Database | MySQL (XAMPP) |
| Frontend | Bootstrap 5.3.2, Bootstrap Icons 1.11.3 |
| Charts | Chart.js 4.4.1 |
| Auth | Session-based, SHA-256 password hashing |

---

