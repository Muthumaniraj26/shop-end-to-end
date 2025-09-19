from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change_this_secret"

DB_CONF = {
    "host":"localhost",
    "database":"shopdb",
    "user":"postgres",
    "password":"2004"
}

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
    return render_template("admin.html", username=user["username"])

@app.route("/shopkeeper")
def shopkeeper_dashboard():
    user = current_user()
    if not user or user["role"]!="shopkeeper":
        return redirect(url_for("login"))
    return render_template("shopkeeper.html", username=user["username"])

@app.route("/worker")
def worker_dashboard():
    user = current_user()
    if not user or user["role"]!="worker":
        return redirect(url_for("login"))
    return render_template("worker.html", username=user["username"])

# ---------------- Admin APIs -----------------
@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    user = current_user()
    if not user or user["role"]!="admin":
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

if __name__=="__main__":
    app.run(debug=True, port=5000)
