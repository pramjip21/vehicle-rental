from datetime import datetime
from functools import wraps
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from database import create_database, get_connection

app = Flask(__name__)
app.secret_key = "vehicle_rental_management_secret_key"

create_database()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_connection()
        admin = conn.execute(
            "SELECT * FROM admin WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin_id"] = admin["admin_id"]
            session["username"] = admin["username"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_connection()

    total_vehicles = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    available_vehicles = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE status = 'Available'"
    ).fetchone()[0]
    rented_vehicles = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE status = 'Rented'"
    ).fetchone()[0]
    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_bookings = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    total_revenue = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE payment_status = 'Paid'
    """).fetchone()[0]

    recent_bookings = conn.execute("""
        SELECT 
            b.booking_id,
            c.name AS customer_name,
            v.vehicle_name,
            b.start_date,
            b.end_date,
            b.total_amount,
            b.status
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        ORDER BY b.booking_id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        rented_vehicles=rented_vehicles,
        total_customers=total_customers,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        recent_bookings=recent_bookings
    )


@app.route("/vehicles", methods=["GET", "POST"])
@login_required
def vehicles():
    conn = get_connection()

    if request.method == "POST":
        vehicle_name = request.form.get("vehicle_name")
        vehicle_type = request.form.get("vehicle_type")
        brand = request.form.get("brand")
        model = request.form.get("model")
        vehicle_number = request.form.get("vehicle_number")
        rent_per_day = request.form.get("rent_per_day")
        status = request.form.get("status")

        try:
            conn.execute("""
                INSERT INTO vehicles
                (vehicle_name, vehicle_type, brand, model, vehicle_number, rent_per_day, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                vehicle_name,
                vehicle_type,
                brand,
                model,
                vehicle_number,
                rent_per_day,
                status
            ))
            conn.commit()
            flash("Vehicle added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("Vehicle number already exists.", "danger")

        conn.close()
        return redirect(url_for("vehicles"))

    search = request.args.get("search", "")

    if search:
        vehicle_list = conn.execute("""
            SELECT * FROM vehicles
            WHERE vehicle_name LIKE ?
               OR vehicle_type LIKE ?
               OR brand LIKE ?
               OR vehicle_number LIKE ?
            ORDER BY vehicle_id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()
    else:
        vehicle_list = conn.execute("""
            SELECT * FROM vehicles
            ORDER BY vehicle_id DESC
        """).fetchall()

    conn.close()
    return render_template("vehicles.html", vehicles=vehicle_list, search=search)


@app.route("/delete_vehicle/<int:vehicle_id>")
@login_required
def delete_vehicle(vehicle_id):
    conn = get_connection()

    vehicle = conn.execute(
        "SELECT * FROM vehicles WHERE vehicle_id = ?",
        (vehicle_id,)
    ).fetchone()

    if vehicle and vehicle["status"] == "Rented":
        flash("Cannot delete rented vehicle.", "danger")
    else:
        conn.execute("DELETE FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        conn.commit()
        flash("Vehicle deleted successfully.", "success")

    conn.close()
    return redirect(url_for("vehicles"))


@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    conn = get_connection()

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        license_no = request.form.get("license_no")
        address = request.form.get("address")

        try:
            conn.execute("""
                INSERT INTO customers
                (name, phone, email, license_no, address)
                VALUES (?, ?, ?, ?, ?)
            """, (name, phone, email, license_no, address))
            conn.commit()
            flash("Customer added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("License number already exists.", "danger")

        conn.close()
        return redirect(url_for("customers"))

    search = request.args.get("search", "")

    if search:
        customer_list = conn.execute("""
            SELECT * FROM customers
            WHERE name LIKE ?
               OR phone LIKE ?
               OR email LIKE ?
               OR license_no LIKE ?
            ORDER BY customer_id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()
    else:
        customer_list = conn.execute("""
            SELECT * FROM customers
            ORDER BY customer_id DESC
        """).fetchall()

    conn.close()
    return render_template("customers.html", customers=customer_list, search=search)


@app.route("/delete_customer/<int:customer_id>")
@login_required
def delete_customer(customer_id):
    conn = get_connection()

    booking = conn.execute(
        "SELECT * FROM bookings WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()

    if booking:
        flash("Cannot delete customer with booking history.", "danger")
    else:
        conn.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
        conn.commit()
        flash("Customer deleted successfully.", "success")

    conn.close()
    return redirect(url_for("customers"))


@app.route("/bookings", methods=["GET", "POST"])
@login_required
def bookings():
    conn = get_connection()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        vehicle_id = request.form.get("vehicle_id")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        vehicle = conn.execute(
            "SELECT * FROM vehicles WHERE vehicle_id = ?",
            (vehicle_id,)
        ).fetchone()

        if vehicle is None:
            conn.close()
            flash("Vehicle not found.", "danger")
            return redirect(url_for("bookings"))

        if vehicle["status"] != "Available":
            conn.close()
            flash("Selected vehicle is not available.", "danger")
            return redirect(url_for("bookings"))

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            conn.close()
            flash("Invalid date.", "danger")
            return redirect(url_for("bookings"))

        total_days = (end - start).days + 1

        if total_days <= 0:
            conn.close()
            flash("End date must be after start date.", "danger")
            return redirect(url_for("bookings"))

        total_amount = total_days * vehicle["rent_per_day"]

        conn.execute("""
            INSERT INTO bookings
            (customer_id, vehicle_id, start_date, end_date, total_days, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            vehicle_id,
            start_date,
            end_date,
            total_days,
            total_amount,
            "Booked"
        ))

        conn.execute(
            "UPDATE vehicles SET status = 'Rented' WHERE vehicle_id = ?",
            (vehicle_id,)
        )

        conn.commit()
        conn.close()

        flash("Booking created successfully.", "success")
        return redirect(url_for("bookings"))

    customers_list = conn.execute("""
        SELECT * FROM customers
        ORDER BY name ASC
    """).fetchall()

    vehicles_list = conn.execute("""
        SELECT * FROM vehicles
        WHERE status = 'Available'
        ORDER BY vehicle_name ASC
    """).fetchall()

    booking_list = conn.execute("""
        SELECT
            b.booking_id,
            c.name AS customer_name,
            v.vehicle_name,
            v.vehicle_number,
            b.start_date,
            b.end_date,
            b.total_days,
            b.total_amount,
            b.status
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        ORDER BY b.booking_id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "bookings.html",
        customers=customers_list,
        vehicles=vehicles_list,
        bookings=booking_list
    )


@app.route("/complete_booking/<int:booking_id>")
@login_required
def complete_booking(booking_id):
    conn = get_connection()

    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id = ?",
        (booking_id,)
    ).fetchone()

    if booking:
        conn.execute(
            "UPDATE bookings SET status = 'Completed' WHERE booking_id = ?",
            (booking_id,)
        )

        conn.execute(
            "UPDATE vehicles SET status = 'Available' WHERE vehicle_id = ?",
            (booking["vehicle_id"],)
        )

        conn.commit()
        flash("Booking completed and vehicle returned.", "success")
    else:
        flash("Booking not found.", "danger")

    conn.close()
    return redirect(url_for("bookings"))


@app.route("/cancel_booking/<int:booking_id>")
@login_required
def cancel_booking(booking_id):
    conn = get_connection()

    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id = ?",
        (booking_id,)
    ).fetchone()

    if booking:
        conn.execute(
            "UPDATE bookings SET status = 'Cancelled' WHERE booking_id = ?",
            (booking_id,)
        )

        conn.execute(
            "UPDATE vehicles SET status = 'Available' WHERE vehicle_id = ?",
            (booking["vehicle_id"],)
        )

        conn.commit()
        flash("Booking cancelled successfully.", "success")
    else:
        flash("Booking not found.", "danger")

    conn.close()
    return redirect(url_for("bookings"))


@app.route("/payments", methods=["GET", "POST"])
@login_required
def payments():
    conn = get_connection()

    if request.method == "POST":
        booking_id = request.form.get("booking_id")
        amount = request.form.get("amount")
        payment_method = request.form.get("payment_method")
        payment_status = request.form.get("payment_status")
        payment_date = request.form.get("payment_date")

        conn.execute("""
            INSERT INTO payments
            (booking_id, amount, payment_method, payment_status, payment_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            booking_id,
            amount,
            payment_method,
            payment_status,
            payment_date
        ))

        conn.commit()
        conn.close()

        flash("Payment added successfully.", "success")
        return redirect(url_for("payments"))

    bookings_list = conn.execute("""
        SELECT
            b.booking_id,
            c.name AS customer_name,
            v.vehicle_name,
            b.total_amount,
            b.status
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        WHERE b.status != 'Cancelled'
        ORDER BY b.booking_id DESC
    """).fetchall()

    payment_list = conn.execute("""
        SELECT
            p.payment_id,
            p.booking_id,
            c.name AS customer_name,
            v.vehicle_name,
            p.amount,
            p.payment_method,
            p.payment_status,
            p.payment_date
        FROM payments p
        JOIN bookings b ON p.booking_id = b.booking_id
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        ORDER BY p.payment_id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "payments.html",
        bookings=bookings_list,
        payments=payment_list
    )


@app.route("/delete_payment/<int:payment_id>")
@login_required
def delete_payment(payment_id):
    conn = get_connection()
    conn.execute("DELETE FROM payments WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()

    flash("Payment deleted successfully.", "success")
    return redirect(url_for("payments"))


if __name__ == "__main__":
    app.run(debug=True)