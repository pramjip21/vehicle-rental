import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_FOLDER = "database"
DB_NAME = "rental.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_name TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            vehicle_number TEXT NOT NULL UNIQUE,
            rent_per_day REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            license_no TEXT NOT NULL UNIQUE,
            address TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_days INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked',
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(booking_id)
        )
    """)

    cursor.execute("SELECT * FROM admin WHERE username = ?", ("admin",))
    admin = cursor.fetchone()

    if admin is None:
        hashed_password = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            ("admin", hashed_password)
        )

    cursor.execute("SELECT COUNT(*) FROM vehicles")
    vehicle_count = cursor.fetchone()[0]

    if vehicle_count == 0:
        sample_vehicles = [
            ("Honda Activa", "Bike", "Honda", "2022", "TN69AB1234", 500, "Available"),
            ("Royal Enfield Classic", "Bike", "Royal Enfield", "2021", "TN69RE5678", 1200, "Available"),
            ("Maruti Swift", "Car", "Maruti Suzuki", "2023", "TN69SW1111", 1800, "Available"),
            ("Hyundai i20", "Car", "Hyundai", "2022", "TN69HY2222", 2200, "Available"),
            ("Toyota Innova", "Car", "Toyota", "2021", "TN69TO3333", 3500, "Available")
        ]

        cursor.executemany("""
            INSERT INTO vehicles
            (vehicle_name, vehicle_type, brand, model, vehicle_number, rent_per_day, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_vehicles)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
    print("Database created successfully.")