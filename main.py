from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect, url_for, jsonify, request
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
from fpdf import FPDF
import os
import datetime
app = Flask(__name__)
app.secret_key = "change_this_secret"

DB_CONF = {
    "host":"localhost",
    "database":"shopdb",
    "user":"postgres",
    "password":"2004"
}
def get_db():
    return psycopg2.connect(**DB_CONF, cursor_factory=RealDictCursor)

def get_db_connection():
    return psycopg2.connect(**DB_CONF)


# Initialize DB and create default admin
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password_hash VARCHAR(200),
            role VARCHAR(20)
        )
    """)
    # Add default admin
    cur.execute("SELECT * FROM users WHERE username='muthu'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (%s,%s,%s)",
                    ('muthu', generate_password_hash('mutu1234'), 'admin'))
    conn.commit()
    cur.close(); conn.close()

init_db()
def init_product_sales():
    conn = get_db_connection()
    cur = conn.cursor()
    # Products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            price NUMERIC(10,2),
            stock INT
        )
    """)
    # Sales table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            product_id INT,
            qty INT,
            price NUMERIC(10,2),
            sold_by VARCHAR(50),
            sold_at TIMESTAMP
        )
    """)
    conn.commit()
    cur.close(); conn.close()

init_product_sales()

# ---------------- Auth -----------------
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, role FROM users WHERE username=%s",(username,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row and check_password_hash(row[1], password):
            session["user_id"] = row[0]
            session["role"] = row[2]
            session["username"] = username
            if row[2]=="admin":
                return redirect(url_for("admin_dashboard"))
            elif row[2]=="shopkeeper":
                return redirect(url_for("shopkeeper_dashboard"))
            else:
                return redirect(url_for("worker_dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def current_user():
    if "user_id" not in session:
        return None
    return {"id":session["user_id"],"username":session["username"],"role":session["role"]}

# ---------------- Dashboards -----------------
@app.route("/admin")
def admin_dashboard():
    user = current_user()
    if not user or user["role"]!="admin":
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetch users (exclude admin)
    cur.execute("SELECT id, username, role FROM users WHERE role != 'admin'")
    users = cur.fetchall()
    # Fetch products
    cur.execute("SELECT id, name, price, stock FROM products")
    products = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin.html", username=user["username"], users=users, products=products)
@app.route("/admin/delete_user/<int:user_id>", methods=["GET","POST"])
def admin_delete_user(user_id):
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    # Optional: prevent deleting admin
    cur.execute("DELETE FROM users WHERE id=%s AND role != 'admin'", (user_id,))
    conn.commit()
    cur.close(); conn.close()

    return redirect(url_for("admin_dashboard"))



@app.route("/shopkeeper")
def shopkeeper_dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY id;")
    products = cur.fetchall()
    cur.execute("""SELECT c.id, p.name, p.price, c.qty 
                   FROM cart c JOIN products p ON c.product_id=p.id;""")
    cart_items = cur.fetchall()
    conn.close()
    return render_template("shopkeeper.html", products=products, cart=cart_items)
@app.route("/cart/add/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form["qty"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO cart (product_id, qty, added_by) VALUES (%s,%s,%s);",
                (pid, qty, session.get("username", "keeper")))
    conn.commit()
    conn.close()
    flash("Product added to cart.")
    return redirect(url_for("shopkeeper_dashboard"))
from flask import request, render_template, flash, send_file
from fpdf import FPDF
import os, datetime

@app.route("/cart/pay", methods=["GET", "POST"])
def pay_cart():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch cart items for display
    cur.execute("""
        SELECT p.name, c.qty, p.price, c.product_id
        FROM cart c
        JOIN products p ON c.product_id = p.id
    """)
    cart_items = cur.fetchall()

    total = sum(price * qty for name, qty, price, pid in cart_items)

    if request.method == "POST":
        customer_name = request.form.get("customer_name")
        payment_method = request.form.get("payment_method")

        # Generate PDF first
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "", 16)
        pdf.cell(0, 10, "Shop Bill", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Customer: {customer_name}", ln=True)
        pdf.cell(0, 10, f"Payment Method: {payment_method}", ln=True)
        pdf.ln(5)

        pdf.cell(70, 10, "Product", border=1)
        pdf.cell(30, 10, "Qty", border=1)
        pdf.cell(30, 10, "Price", border=1)
        pdf.cell(30, 10, "Total", border=1, ln=True)

        for name, qty, price, pid in cart_items:
            line_total = price * qty
            pdf.cell(70, 10, name, border=1)
            pdf.cell(30, 10, str(qty), border=1)
            pdf.cell(30, 10, f"{price:.2f}", border=1)
            pdf.cell(30, 10, f"{line_total:.2f}", border=1, ln=True)

        pdf.ln(5)
        pdf.cell(0, 10, f"Total Paid: {total:.2f}", ln=True)

        # Save PDF
        os.makedirs("bills", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = f"bills/bill_{timestamp}.pdf"
        pdf.output(pdf_path)

        # Deduct stock and log sales **after PDF is generated**
        for name, qty, price, pid in cart_items:
            cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (qty, pid))
            cur.execute("INSERT INTO sales (product_id, qty) VALUES (%s, %s)", (pid, qty))

        # Clear cart
        cur.execute("DELETE FROM cart;")
        conn.commit()
        cur.close()
        conn.close()

        flash(f"Payment successful via {payment_method} ✅")
        # Return PDF first, then reload cart page
        return send_file(pdf_path, as_attachment=True)

    cur.close()
    conn.close()
    return render_template("cart_pay.html", cart_items=cart_items, total=total)

@app.route("/cart")
def cart_view():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT p.name, c.qty, p.price, c.product_id FROM cart c JOIN products p ON c.product_id = p.id")
    cart_items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("cart_pay.html", cart_items=cart_items)


@app.route("/cart/back", methods=["GET", "POST"])
def back_cart():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart;")
    conn.commit()
    conn.close()
    flash("Cart cleared and products restored.")
    return redirect(url_for("shopkeeper_dashboard"))

# --- Add to Cart ---
@app.route("/worker")
def worker_dashboard():
    user = current_user()
    if not user or user["role"] != "worker":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, stock FROM products ORDER BY id")
    products = cur.fetchall()
    cur.close(); conn.close()

    return render_template("worker.html", products=products, user=user)

# ---------------- Admin APIs -----------------
@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    user = current_user()
    if not user or user["role"] != "admin":
        return jsonify({"error":"forbidden"}),403
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")
    if not username or not password or role not in ["worker","shopkeeper"]:
        return jsonify({"error":"invalid data"}),400
    pw_hash = generate_password_hash(password)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (%s,%s,%s)",
                    (username,pw_hash,role))
        conn.commit()
        cur.close(); conn.close()
        return jsonify({"message":f"{role} '{username}' created"})
    except Exception as e:
        conn.rollback()
        cur.close(); conn.close()
        return jsonify({"error":str(e)}),400
@app.route("/admin/add_user_form", methods=["POST"])
def admin_add_user_form():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))

    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")

    if not username or not password or role not in ["worker", "shopkeeper"]:
        return "Invalid data", 400

    pw_hash = generate_password_hash(password)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
                    (username, pw_hash, role))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"Error: {str(e)}", 400
    finally:
        cur.close(); conn.close()

    return redirect(url_for("admin_dashboard"))



# ---------------- User password change -----------------
@app.route("/user/change_password", methods=["POST"])
def change_password():
    user = current_user()
    if not user:
        return jsonify({"error":"not logged in"}),401
    data = request.json
    old = data.get("old_password")
    new = data.get("new_password")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id=%s",(user["id"],))
    pw_hash = cur.fetchone()[0]
    if not check_password_hash(pw_hash, old):
        cur.close(); conn.close()
        return jsonify({"error":"Old password incorrect"}),400
    new_hash = generate_password_hash(new)
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",(new_hash,user["id"]))
    conn.commit()
    cur.close(); conn.close()
    return jsonify({"message":"Password changed successfully"})
@app.route("/admin/add_product", methods=["POST"])
def admin_add_product():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))
    
    name = request.form.get("name").strip().lower()
    price = request.form.get("price")
    stock = request.form.get("stock")
    
    if not name or not price or not stock:
        return "Invalid data", 400
    
    try:
        price = float(price)
        stock = int(stock)
    except ValueError:
        return "Price or stock invalid", 400
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if product already exists
    cur.execute("SELECT id, stock FROM products WHERE LOWER(name)=%s", (name,))
    row = cur.fetchone()

    if row:
        # Product exists → update stock only
        pid, current_stock = row
        new_stock = current_stock + stock
        cur.execute("UPDATE products SET stock=%s, price=%s WHERE id=%s", 
                    (new_stock, price, pid))
    else:
        # Insert new product
        cur.execute("INSERT INTO products (name, price, stock) VALUES (%s,%s,%s)", 
                    (name, price, stock))
    
    conn.commit()
    cur.close(); conn.close()
    
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_product/<int:pid>", methods=["GET","POST"])
def admin_delete_product(pid):
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (pid,))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for("admin_dashboard"))
@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    user = current_user()  # however you fetch the logged-in user
    message = None
    history = []  # query from DB if you track requests
    
    if request.method == "POST":
        action = request.form.get("action")

        if action == "change_password":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            # TODO: verify current_password, then update DB
            message = "Password changed successfully."

        elif action == "request_username_change":
            new_username = request.form.get("new_username")
            # TODO: insert into username change requests table
            message = "Username change request submitted."

        elif action == "request_admin_reset":
            # TODO: insert reset request into DB
            message = "Admin reset request submitted."

    return render_template("settings.html",
                           user=user,
                           message=message,
                           history=history)





# ---------------- Shopkeeper Sell -----------------
@app.route("/shopkeeper/sell/<int:pid>", methods=["POST"])
def shopkeeper_sell_product(pid):
    user = current_user()
    if not user or user["role"] != "shopkeeper":
        return redirect(url_for("login"))

    qty = int(request.form.get("qty", 1))  # default 1
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT stock, price FROM products WHERE id=%s", (pid,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return "Product not found", 404
    
    stock, price = row
    if stock < qty:
        cur.close(); conn.close()
        return "Not enough stock", 400
    
    new_stock = stock - qty
    cur.execute("UPDATE products SET stock=%s WHERE id=%s", (new_stock, pid))
    cur.execute("INSERT INTO sales (product_id, qty, price, sold_by, sold_at) VALUES (%s,%s,%s,%s,now())",
                (pid, qty, price, user["username"]))
    
    # Optional: create low-stock request to admin if stock < threshold
    if new_stock < 5:
        # Add to refill_requests table (create if not exists)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refill_requests (
                id SERIAL PRIMARY KEY,
                product_id INT,
                requested_by VARCHAR(50),
                qty INT,
                status VARCHAR(20) DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT now()
            )
        """)
        cur.execute("INSERT INTO refill_requests (product_id, requested_by, qty) VALUES (%s,%s,%s)",
                    (pid, user["username"], 10))  # example refill qty
    
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for("shopkeeper_dashboard"))


# ---------------- Worker Add Product -----------------
@app.route("/worker/add_product", methods=["POST"])
def worker_add_product():
    user = current_user()
    if not user or user["role"] != "worker":
        return jsonify({"error": "forbidden"}), 403

    name = request.form.get("name").strip().lower()
    price = request.form.get("price")
    stock = request.form.get("stock")

    if not name or price is None or stock is None:
        return jsonify({"error": "invalid data"}), 400

    try:
        price = float(price)
        stock = int(stock)
    except ValueError:
        return jsonify({"error": "Price or stock invalid"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if product already exists
    cur.execute("SELECT id, stock FROM products WHERE LOWER(name)=%s", (name,))
    row = cur.fetchone()

    if row:
        # Refill existing product stock
        pid, current_stock = row
        new_stock = current_stock + stock
        cur.execute("UPDATE products SET stock=%s, price=%s WHERE id=%s", 
                    (new_stock, price, pid))
    else:
        # Insert new product
        cur.execute("INSERT INTO products (name, price, stock) VALUES (%s,%s,%s)", 
                    (name, price, stock))

    conn.commit()
    cur.close(); conn.close()

    return redirect(url_for("worker_dashboard"))
@app.route("/worker/refill_product/<int:product_id>", methods=["POST"])
def worker_refill_product(product_id):
    user = current_user()
    if not user or user["role"] != "worker":
        return jsonify({"error": "forbidden"}), 403

    qty = request.form.get("qty")
    if not qty or not qty.isdigit():
        return jsonify({"error": "invalid quantity"}), 400

    qty = int(qty)

    conn = get_db_connection()
    cur = conn.cursor()
    # add stock
    cur.execute(
        "UPDATE products SET stock = stock + %s WHERE id = %s",
        (qty, product_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("worker_dashboard"))



if __name__=="__main__":
    app.run(debug=True, port=5000)
