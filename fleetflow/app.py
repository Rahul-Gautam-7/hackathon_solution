from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import mysql.connector
from mysql.connector import Error
import hashlib
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'fleetflow_secret_key_2024'

# DB Config - XAMPP default settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'fleetflow_db',
    'user': 'root',
    'password': ''       
                         
}

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==================== RBAC CONFIG ====================

WRITE_PERMS = {
    'vehicles':    ['Manager'],
    'trips':       ['Manager', 'Dispatcher'],
    'drivers':     ['Manager', 'Safety Officer'],
    'maintenance': ['Manager', 'Financial Analyst'],
    'expenses':    ['Manager', 'Financial Analyst'],
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied. You do not have permission for this action.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def write_required(module):
    """Decorator that checks if current role can write to the given module."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = session.get('role')
            if role not in WRITE_PERMS.get(module, []):
                flash(f'Access denied. Your role ({role}) cannot modify {module}.', 'danger')
                return redirect(request.referrer or url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


from flask import g
@app.context_processor
def inject_permissions():
    role = session.get('role', '')
    return dict(
        current_role=role,
        can_write_vehicles    = role in WRITE_PERMS['vehicles'],
        can_write_trips       = role in WRITE_PERMS['trips'],
        can_write_drivers     = role in WRITE_PERMS['drivers'],
        can_write_maintenance = role in WRITE_PERMS['maintenance'],
        can_write_expenses    = role in WRITE_PERMS['expenses'],
    )


# ==================== REGISTER ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'Dispatcher')

        # Validation
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        valid_roles = ['Manager', 'Dispatcher', 'Safety Officer', 'Financial Analyst']
        if role not in valid_roles:
            role = 'Dispatcher'

        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
            existing = cursor.fetchone()
            if existing:
                flash('An account with this email already exists.', 'danger')
                conn.close()
                return render_template('register.html')
            # Create user
            hashed = hash_password(password)
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed, role)
            )
            conn.commit()
            conn.close()
            flash(f'Account created successfully! Welcome, {name}. Please sign in.', 'success')
            return redirect(url_for('login'))
        flash('Database connection error. Please try again.', 'danger')
    return render_template('register.html')

# ==================== AUTH ====================

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = get_db()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
            user = cursor.fetchone()
            conn.close()
            if user:
                session['user_id'] = user['id']
                session['username'] = user['name']
                session['role'] = user['role']
                return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    stats = {}
    recent_trips = []
    alerts = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as cnt FROM vehicles WHERE status='On Trip'")
        stats['active_fleet'] = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM vehicles WHERE status='In Shop'")
        stats['maintenance_alerts'] = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM vehicles WHERE status NOT IN ('Out of Service')")
        total = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM vehicles WHERE status='On Trip'")
        assigned = cursor.fetchone()['cnt']
        stats['utilization'] = round((assigned / total * 100) if total > 0 else 0, 1)
        cursor.execute("SELECT COUNT(*) as cnt FROM trips WHERE status='Draft'")
        stats['pending_cargo'] = cursor.fetchone()['cnt']
        cursor.execute("""SELECT t.*, v.name as vehicle_name, d.name as driver_name 
                         FROM trips t 
                         LEFT JOIN vehicles v ON t.vehicle_id=v.id 
                         LEFT JOIN drivers d ON t.driver_id=d.id 
                         ORDER BY t.created_at DESC LIMIT 5""")
        recent_trips = cursor.fetchall()
        cursor.execute("""SELECT d.name, d.license_expiry FROM drivers d 
                         WHERE d.license_expiry <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) 
                         AND d.license_expiry >= CURDATE()""")
        alerts = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as cnt FROM vehicles WHERE status='Available'")
        stats['available_vehicles'] = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM drivers WHERE status='On Duty'")
        stats['on_duty_drivers'] = cursor.fetchone()['cnt']
        conn.close()
    return render_template('dashboard.html', stats=stats, recent_trips=recent_trips, alerts=alerts)

# ==================== VEHICLES ====================

@app.route('/vehicles')
@login_required
def vehicles():
    conn = get_db()
    vehicles = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        type_f = request.args.get('type', '')
        status_f = request.args.get('status', '')
        query = "SELECT * FROM vehicles WHERE 1=1"
        params = []
        if type_f:
            query += " AND type=%s"; params.append(type_f)
        if status_f:
            query += " AND status=%s"; params.append(status_f)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        vehicles = cursor.fetchall()
        conn.close()
    return render_template('vehicles.html', vehicles=vehicles, type_f=request.args.get('type',''), status_f=request.args.get('status',''))

@app.route('/vehicles/add', methods=['POST'])
@login_required
@write_required('vehicles')
def add_vehicle():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO vehicles (name, license_plate, type, max_capacity, odometer, status) 
                             VALUES (%s,%s,%s,%s,%s,'Available')""",
                (request.form['name'], request.form['license_plate'], request.form['type'],
                 request.form['max_capacity'], request.form.get('odometer', 0)))
            conn.commit()
            flash('Vehicle added successfully!', 'success')
        except Error as e:
            flash(f'Error: {e}', 'danger')
        conn.close()
    return redirect(url_for('vehicles'))

@app.route('/vehicles/edit/<int:vid>', methods=['POST'])
@login_required
@write_required('vehicles')
def edit_vehicle(vid):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""UPDATE vehicles SET name=%s, license_plate=%s, type=%s, 
                         max_capacity=%s, odometer=%s WHERE id=%s""",
            (request.form['name'], request.form['license_plate'], request.form['type'],
             request.form['max_capacity'], request.form['odometer'], vid))
        conn.commit()
        conn.close()
        flash('Vehicle updated!', 'success')
    return redirect(url_for('vehicles'))

@app.route('/vehicles/toggle/<int:vid>', methods=['POST'])
@login_required
@write_required('vehicles')
def toggle_vehicle(vid):
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM vehicles WHERE id=%s", (vid,))
        v = cursor.fetchone()
        new_status = 'Out of Service' if v['status'] != 'Out of Service' else 'Available'
        cursor.execute("UPDATE vehicles SET status=%s WHERE id=%s", (new_status, vid))
        conn.commit()
        conn.close()
    return redirect(url_for('vehicles'))

@app.route('/vehicles/delete/<int:vid>', methods=['POST'])
@login_required
@write_required('vehicles')
def delete_vehicle(vid):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehicles WHERE id=%s", (vid,))
        conn.commit()
        conn.close()
        flash('Vehicle deleted.', 'info')
    return redirect(url_for('vehicles'))

# ==================== TRIPS ====================

@app.route('/trips')
@login_required
def trips():
    conn = get_db()
    trips = []
    available_vehicles = []
    available_drivers = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT t.*, v.name as vehicle_name, v.license_plate, d.name as driver_name 
                         FROM trips t 
                         LEFT JOIN vehicles v ON t.vehicle_id=v.id 
                         LEFT JOIN drivers d ON t.driver_id=d.id 
                         ORDER BY t.created_at DESC""")
        trips = cursor.fetchall()
        cursor.execute("SELECT * FROM vehicles WHERE status='Available' ORDER BY name")
        available_vehicles = cursor.fetchall()
        # Show all drivers except Suspended — warn about expired license but don't block
        cursor.execute("SELECT *, CASE WHEN license_expiry < CURDATE() THEN 1 ELSE 0 END as license_expired FROM drivers WHERE status != 'Suspended' ORDER BY name")
        available_drivers = cursor.fetchall()
        conn.close()
    return render_template('trips.html', trips=trips, vehicles=available_vehicles, drivers=available_drivers)

@app.route('/trips/add', methods=['POST'])
@login_required
@write_required('trips')
def add_trip():
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        vid = request.form['vehicle_id']
        did = request.form['driver_id']
        cargo_weight = float(request.form['cargo_weight'])
        cursor.execute("SELECT max_capacity FROM vehicles WHERE id=%s", (vid,))
        vehicle = cursor.fetchone()
        if vehicle and cargo_weight > vehicle['max_capacity']:
            flash(f"Cargo weight ({cargo_weight}kg) exceeds vehicle capacity ({vehicle['max_capacity']}kg)!", 'danger')
            conn.close()
            return redirect(url_for('trips'))
        cursor.execute("""INSERT INTO trips (vehicle_id, driver_id, origin, destination, cargo_weight, cargo_desc, status) 
                         VALUES (%s,%s,%s,%s,%s,%s,'Draft')""",
            (vid, did, request.form['origin'], request.form['destination'],
             cargo_weight, request.form.get('cargo_desc','')))
        conn.commit()
        conn.close()
        flash('Trip created successfully!', 'success')
    return redirect(url_for('trips'))


@app.route('/trips/edit/<int:tid>', methods=['POST'])
@login_required
@write_required('trips')
def edit_trip(tid):
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # allow editing if trip is still Draft
        cursor.execute("SELECT * FROM trips WHERE id=%s AND status='Draft'", (tid,))
        trip = cursor.fetchone()
        if not trip:
            flash('Only Draft trips can be edited.', 'danger')
            conn.close()
            return redirect(url_for('trips'))
        vid = request.form['vehicle_id']
        did = request.form['driver_id']
        cargo_weight = float(request.form['cargo_weight'])
        cursor.execute("SELECT max_capacity FROM vehicles WHERE id=%s", (vid,))
        vehicle = cursor.fetchone()
        if vehicle and cargo_weight > vehicle['max_capacity']:
            flash(f"Cargo weight ({cargo_weight}kg) exceeds vehicle capacity ({vehicle['max_capacity']}kg)!", 'danger')
            conn.close()
            return redirect(url_for('trips'))
        cursor.execute("""UPDATE trips SET vehicle_id=%s, driver_id=%s, origin=%s, 
                         destination=%s, cargo_weight=%s, cargo_desc=%s WHERE id=%s AND status='Draft'""",
            (vid, did, request.form['origin'], request.form['destination'],
             cargo_weight, request.form.get('cargo_desc',''), tid))
        conn.commit()
        conn.close()
        flash('Trip updated successfully!', 'success')
    return redirect(url_for('trips'))

@app.route('/trips/update_status/<int:tid>', methods=['POST'])
@login_required
@write_required('trips')
def update_trip_status(tid):
    new_status = request.form['status']
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trips WHERE id=%s", (tid,))
        trip = cursor.fetchone()
        if trip:
            cursor.execute("UPDATE trips SET status=%s WHERE id=%s", (new_status, tid))
            if new_status == 'Dispatched':
                cursor.execute("UPDATE vehicles SET status='On Trip' WHERE id=%s", (trip['vehicle_id'],))
                cursor.execute("UPDATE drivers SET status='On Duty' WHERE id=%s", (trip['driver_id'],))
            elif new_status in ('Completed', 'Cancelled'):
                odometer = request.form.get('final_odometer')
                if odometer:
                    cursor.execute("UPDATE vehicles SET odometer=%s WHERE id=%s", (odometer, trip['vehicle_id']))
                cursor.execute("UPDATE vehicles SET status='Available' WHERE id=%s", (trip['vehicle_id'],))
                cursor.execute("UPDATE drivers SET status='On Duty' WHERE id=%s", (trip['driver_id'],))
                if new_status == 'Completed':
                    cursor.execute("UPDATE drivers SET trips_completed=trips_completed+1 WHERE id=%s", (trip['driver_id'],))
            conn.commit()
        conn.close()
        flash(f'Trip status updated to {new_status}', 'success')
    return redirect(url_for('trips'))

# ==================== MAINTENANCE ====================

@app.route('/maintenance')
@login_required
def maintenance():
    conn = get_db()
    logs = []
    vehicles_list = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT m.*, v.name as vehicle_name, v.license_plate 
                         FROM maintenance_logs m 
                         LEFT JOIN vehicles v ON m.vehicle_id=v.id 
                         ORDER BY m.service_date DESC""")
        logs = cursor.fetchall()
        cursor.execute("SELECT * FROM vehicles WHERE status != 'Out of Service'")
        vehicles_list = cursor.fetchall()
        conn.close()
    return render_template('maintenance.html', logs=logs, vehicles=vehicles_list)

@app.route('/maintenance/add', methods=['POST'])
@login_required
@write_required('maintenance')
def add_maintenance():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        vid = request.form['vehicle_id']
        cursor.execute("""INSERT INTO maintenance_logs (vehicle_id, service_type, description, cost, service_date, mechanic) 
                         VALUES (%s,%s,%s,%s,%s,%s)""",
            (vid, request.form['service_type'], request.form.get('description',''),
             request.form.get('cost', 0), request.form['service_date'], request.form.get('mechanic','')))
        cursor.execute("UPDATE vehicles SET status='In Shop' WHERE id=%s", (vid,))
        conn.commit()
        conn.close()
        flash('Maintenance logged. Vehicle marked as In Shop.', 'success')
    return redirect(url_for('maintenance'))

@app.route('/maintenance/complete/<int:mid>', methods=['POST'])
@login_required
@write_required('maintenance')
def complete_maintenance(mid):
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT vehicle_id FROM maintenance_logs WHERE id=%s", (mid,))
        log = cursor.fetchone()
        cursor.execute("UPDATE maintenance_logs SET status='Completed', completed_date=CURDATE() WHERE id=%s", (mid,))
        cursor.execute("UPDATE vehicles SET status='Available' WHERE id=%s AND status='In Shop'", (log['vehicle_id'],))
        conn.commit()
        conn.close()
        flash('Maintenance completed. Vehicle now Available.', 'success')
    return redirect(url_for('maintenance'))

# ==================== FUEL / EXPENSES ====================

@app.route('/expenses')
@login_required
def expenses():
    conn = get_db()
    logs = []
    trips_list = []
    vehicles_list = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT f.*, v.name as vehicle_name, t.origin, t.destination 
                         FROM fuel_logs f 
                         LEFT JOIN vehicles v ON f.vehicle_id=v.id 
                         LEFT JOIN trips t ON f.trip_id=t.id 
                         ORDER BY f.log_date DESC""")
        logs = cursor.fetchall()
        cursor.execute("SELECT id, vehicle_id, origin, destination FROM trips WHERE status='Completed' ORDER BY created_at DESC")
        trips_list = cursor.fetchall()
        cursor.execute("SELECT * FROM vehicles WHERE status != 'Out of Service'")
        vehicles_list = cursor.fetchall()
        conn.close()
    return render_template('expenses.html', logs=logs, trips=trips_list, vehicles=vehicles_list)

@app.route('/expenses/add', methods=['POST'])
@login_required
@write_required('expenses')
def add_expense():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO fuel_logs (vehicle_id, trip_id, liters, cost, odometer_reading, log_date, notes) 
                         VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (request.form['vehicle_id'], request.form.get('trip_id') or None,
             request.form['liters'], request.form['cost'],
             request.form.get('odometer_reading') or None,
             request.form['log_date'], request.form.get('notes','')))
        conn.commit()
        conn.close()
        flash('Fuel log added!', 'success')
    return redirect(url_for('expenses'))

# ==================== DRIVERS ====================

@app.route('/drivers')
@login_required
def drivers():
    conn = get_db()
    drivers_list = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM drivers ORDER BY created_at DESC")
        drivers_list = cursor.fetchall()
        conn.close()
    return render_template('drivers.html', drivers=drivers_list, now=datetime.now())

@app.route('/drivers/add', methods=['POST'])
@login_required
@write_required('drivers')
def add_driver():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO drivers (name, email, phone, license_number, license_expiry, vehicle_category, status) 
                             VALUES (%s,%s,%s,%s,%s,%s,'On Duty')""",
                (request.form['name'], request.form.get('email',''), request.form.get('phone',''),
                 request.form['license_number'], request.form['license_expiry'], request.form.get('vehicle_category','Any')))
            conn.commit()
            flash('Driver added!', 'success')
        except Error as e:
            flash(f'Error: {e}', 'danger')
        conn.close()
    return redirect(url_for('drivers'))

@app.route('/drivers/edit/<int:did>', methods=['POST'])
@login_required
@write_required('drivers')
def edit_driver(did):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""UPDATE drivers SET name=%s, email=%s, phone=%s, license_number=%s, 
                         license_expiry=%s, vehicle_category=%s, safety_score=%s WHERE id=%s""",
            (request.form['name'], request.form.get('email',''), request.form.get('phone',''),
             request.form['license_number'], request.form['license_expiry'],
             request.form.get('vehicle_category','Any'), request.form.get('safety_score',100), did))
        conn.commit()
        conn.close()
        flash('Driver updated!', 'success')
    return redirect(url_for('drivers'))

@app.route('/drivers/toggle_status/<int:did>', methods=['POST'])
@login_required
@write_required('drivers')
def toggle_driver_status(did):
    new_status = request.form['status']
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE drivers SET status=%s WHERE id=%s", (new_status, did))
        conn.commit()
        conn.close()
    return redirect(url_for('drivers'))

@app.route('/drivers/delete/<int:did>', methods=['POST'])
@login_required
@write_required('drivers')
def delete_driver(did):
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM drivers WHERE id=%s", (did,))
        conn.commit()
        conn.close()
        flash('Driver removed.', 'info')
    return redirect(url_for('drivers'))

# ==================== ANALYTICS ====================

@app.route('/analytics')
@login_required
def analytics():
    conn = get_db()
    data = {}
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Fuel efficiency per vehicle
        cursor.execute("""
            SELECT v.name, v.license_plate, v.odometer as current_odometer,
                   SUM(f.liters) as total_liters,
                   SUM(f.cost) as total_fuel_cost,
                   MAX(f.odometer_reading) as max_odometer,
                   MIN(f.odometer_reading) as min_odometer,
                   COUNT(f.id) as log_count
            FROM fuel_logs f
            LEFT JOIN vehicles v ON f.vehicle_id=v.id
            GROUP BY f.vehicle_id, v.name, v.license_plate, v.odometer
        """)
        fuel_data = cursor.fetchall()
        for row in fuel_data:
            total_liters = float(row['total_liters'] or 0)
            if total_liters <= 0:
                row['efficiency'] = '—'
                row['km_driven'] = 0
                continue
           
            max_odo = row['max_odometer']
            min_odo = row['min_odometer']
            if max_odo and min_odo and max_odo > min_odo:
                km = float(max_odo) - float(min_odo)
         
            elif row['current_odometer'] and min_odo and float(row['current_odometer']) > float(min_odo):
                km = float(row['current_odometer']) - float(min_odo)
           
            elif row['current_odometer'] and float(row['current_odometer']) > 0:
                km = float(row['current_odometer'])
            else:
                row['efficiency'] = '—'
                row['km_driven'] = 0
                continue
            row['km_driven'] = round(km, 1)
            row['efficiency'] = round(km / total_liters, 2)
        data['fuel_data'] = fuel_data

        # Total costs per vehicle
        cursor.execute("""
            SELECT v.id, v.name, v.license_plate,
                   COALESCE(SUM(f.cost), 0) as fuel_cost,
                   COALESCE((SELECT SUM(cost) FROM maintenance_logs m WHERE m.vehicle_id=v.id), 0) as maint_cost
            FROM vehicles v
            LEFT JOIN fuel_logs f ON f.vehicle_id=v.id
            GROUP BY v.id
        """)
        cost_data = cursor.fetchall()
        for row in cost_data:
            row['total_cost'] = float(row['fuel_cost']) + float(row['maint_cost'])
        data['cost_data'] = cost_data

        # Trip stats
        cursor.execute("SELECT status, COUNT(*) as cnt FROM trips GROUP BY status")
        data['trip_stats'] = cursor.fetchall()

        # Monthly fuel costs
        cursor.execute("""SELECT DATE_FORMAT(log_date,'%Y-%m') as month, SUM(cost) as cost
                         FROM fuel_logs GROUP BY month ORDER BY month DESC LIMIT 12""")
        data['monthly_fuel'] = cursor.fetchall()

        # Driver performance
        cursor.execute("SELECT name, trips_completed, safety_score FROM drivers ORDER BY trips_completed DESC")
        data['driver_perf'] = cursor.fetchall()

        conn.close()
    return render_template('analytics.html', data=data)

# ==================== API ENDPOINTS ====================

@app.route('/api/vehicle_capacity/<int:vid>')
@login_required
def api_vehicle_capacity(vid):
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT max_capacity FROM vehicles WHERE id=%s", (vid,))
        v = cursor.fetchone()
        conn.close()
        if v:
            return jsonify({'max_capacity': v['max_capacity']})
    return jsonify({'max_capacity': 0})

if __name__ == '__main__':
    app.run(debug=True, port=5000)