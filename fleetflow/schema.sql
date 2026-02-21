-- FleetFlow Database Schema
-- Run this in MySQL to set up the database

CREATE DATABASE IF NOT EXISTS fleetflow_db;
USE fleetflow_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(256) NOT NULL,
    role ENUM('Manager','Dispatcher','Safety Officer','Financial Analyst') DEFAULT 'Dispatcher',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    license_plate VARCHAR(30) UNIQUE NOT NULL,
    type ENUM('Truck','Van','Bike') DEFAULT 'Van',
    max_capacity DECIMAL(10,2) NOT NULL COMMENT 'in kg',
    odometer DECIMAL(10,2) DEFAULT 0 COMMENT 'in km',
    status ENUM('Available','On Trip','In Shop','Out of Service') DEFAULT 'Available',
    region VARCHAR(50) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Drivers table
CREATE TABLE IF NOT EXISTS drivers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) DEFAULT '',
    phone VARCHAR(20) DEFAULT '',
    license_number VARCHAR(50) UNIQUE NOT NULL,
    license_expiry DATE NOT NULL,
    vehicle_category ENUM('Any','Truck','Van','Bike') DEFAULT 'Any',
    status ENUM('On Duty','Off Duty','Suspended') DEFAULT 'On Duty',
    safety_score INT DEFAULT 100,
    trips_completed INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trips table
CREATE TABLE IF NOT EXISTS trips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT,
    driver_id INT,
    origin VARCHAR(200) NOT NULL,
    destination VARCHAR(200) NOT NULL,
    cargo_weight DECIMAL(10,2) NOT NULL COMMENT 'in kg',
    cargo_desc TEXT DEFAULT '',
    status ENUM('Draft','Dispatched','Completed','Cancelled') DEFAULT 'Draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL
);

-- Maintenance logs table
CREATE TABLE IF NOT EXISTS maintenance_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT,
    service_type VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '',
    cost DECIMAL(10,2) DEFAULT 0,
    service_date DATE NOT NULL,
    mechanic VARCHAR(100) DEFAULT '',
    status ENUM('Ongoing','Completed') DEFAULT 'Ongoing',
    completed_date DATE DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
);

-- Fuel logs table
CREATE TABLE IF NOT EXISTS fuel_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT,
    trip_id INT DEFAULT NULL,
    liters DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    odometer_reading DECIMAL(10,2) DEFAULT NULL,
    log_date DATE NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL
);

-- ===================== SEED DATA =====================

-- Default users (password = "admin123" hashed)
-- SHA256 of "admin123" = 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
INSERT IGNORE INTO users (name, email, password, role) VALUES
('Admin Manager', 'admin@fleetflow.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Manager'),
('John Dispatcher', 'dispatch@fleetflow.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Dispatcher'),
('Sara Safety', 'safety@fleetflow.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Safety Officer'),
('Mike Finance', 'finance@fleetflow.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Financial Analyst');

-- Sample vehicles
INSERT IGNORE INTO vehicles (name, license_plate, type, max_capacity, odometer, status, region) VALUES
('Truck-01 Volvo FH', 'TRK-001-AB', 'Truck', 5000, 45230, 'Available', 'North'),
('Truck-02 MAN TGX', 'TRK-002-CD', 'Truck', 8000, 78900, 'In Shop', 'South'),
('Van-01 Ford Transit', 'VAN-001-EF', 'Van', 1500, 23400, 'Available', 'East'),
('Van-02 Mercedes Sprinter', 'VAN-002-GH', 'Van', 1200, 15600, 'On Trip', 'West'),
('Van-03 Iveco Daily', 'VAN-003-IJ', 'Van', 1800, 8900, 'Available', 'North'),
('Bike-01 Royal Enfield', 'BIKE-001-KL', 'Bike', 50, 5600, 'Available', 'City'),
('Bike-02 Honda CB', 'BIKE-002-MN', 'Bike', 50, 12300, 'Available', 'City'),
('Van-05 Toyota HiAce', 'VAN-005-OP', 'Van', 500, 31200, 'Available', 'South');

-- Sample drivers
INSERT IGNORE INTO drivers (name, email, phone, license_number, license_expiry, vehicle_category, status, safety_score, trips_completed) VALUES
('Alex Johnson', 'alex@example.com', '9876543210', 'DL-2024-001', '2026-06-30', 'Van', 'On Duty', 95, 47),
('Maria Garcia', 'maria@example.com', '9876543211', 'DL-2024-002', '2025-12-31', 'Truck', 'On Duty', 88, 112),
('Robert Chen', 'robert@example.com', '9876543212', 'DL-2024-003', '2024-03-15', 'Any', 'Off Duty', 72, 23),
('Priya Sharma', 'priya@example.com', '9876543213', 'DL-2024-004', '2027-01-20', 'Van', 'On Duty', 98, 89),
('James Wilson', 'james@example.com', '9876543214', 'DL-2024-005', '2026-08-15', 'Bike', 'On Duty', 91, 156),
('Lisa Thompson', 'lisa@example.com', '9876543215', 'DL-2024-006', '2025-03-10', 'Truck', 'Suspended', 65, 34);

-- Sample trips
INSERT IGNORE INTO trips (vehicle_id, driver_id, origin, destination, cargo_weight, cargo_desc, status) VALUES
(4, 4, 'Mumbai Warehouse', 'Delhi Distribution Hub', 1100, 'Electronics - fragile', 'Dispatched'),
(1, 2, 'Chennai Port', 'Bangalore Factory', 4500, 'Auto parts batch #A45', 'Completed'),
(3, 1, 'Pune Depot', 'Nashik Store', 1200, 'FMCG goods', 'Completed'),
(6, 5, 'City Hub', 'Sector 5 Delivery', 40, 'Documents & parcels', 'Completed'),
(5, 4, 'Hyderabad WH', 'Vijayawada Store', 1600, 'Textiles', 'Draft');

-- Sample maintenance logs
INSERT IGNORE INTO maintenance_logs (vehicle_id, service_type, description, cost, service_date, mechanic, status) VALUES
(2, 'Engine Overhaul', 'Full engine inspection and overhaul. Replace worn pistons.', 45000, CURDATE(), 'Raju Auto Works', 'Ongoing'),
(1, 'Oil Change', 'Routine engine oil and filter change', 1500, DATE_SUB(CURDATE(), INTERVAL 15 DAY), 'Quick Service', 'Completed'),
(4, 'Tyre Replacement', 'Replace all 4 tyres - worn tread', 12000, DATE_SUB(CURDATE(), INTERVAL 30 DAY), 'Goodyear Service', 'Completed');

-- Sample fuel logs
INSERT IGNORE INTO fuel_logs (vehicle_id, trip_id, liters, cost, odometer_reading, log_date, notes) VALUES
(1, 2, 120, 10800, 78900, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'Full tank before long haul'),
(3, 3, 45, 4050, 23400, DATE_SUB(CURDATE(), INTERVAL 8 DAY), ''),
(6, 4, 8, 720, 5600, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 'City delivery run'),
(4, 1, 65, 5850, 15600, CURDATE(), 'Dispatched today');
