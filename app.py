from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
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

# ---------------- DB ----------------
def get_db_connection():
    conn = psycopg2.connect(**DB_CONF)
    return conn

# Ensure users table exists
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
    # Insert default admin if not exists
    cur.execute("SELECT * FROM users WHERE username='muthu'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (%s,%s,%s)",
                    ('muthu', generate_password_hash('mutu1234'), 'admin'))
    conn.commit()
    cur.close(); conn.close()

init_db()

# ---------------- Auth ----------------
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
            # Redirect to dashboard
            if row[2]=="admin":
                return redirect(url_for("admin_dashboard"))
            elif row[2]=="shopkeeper":
                return redirect(url_for("shopkeeper_dashboard"))
            else:
                return redirect(url_for("worker_dashboard"))
        else:
            error = "Invalid credentials"
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- Helper ----------------
def current_user():
    if "user_id" not in session:
        return None
    return {"id":session["user_id"],"username":session["username"],"role":session["role"]}

# ---------------- Dashboards ----------------
@app.route("/admin")
def admin_dashboard():
    user = current_user()
    if not user or user["role"]!="admin":
        return redirect(url_for("login"))
    return render_template_string(ADMIN_HTML, username=user["username"])

@app.route("/shopkeeper")
def shopkeeper_dashboard():
    user = current_user()
    if not user or user["role"]!="shopkeeper":
        return redirect(url_for("login"))
    return render_template_string(SHOPKEEPER_HTML, username=user["username"])

@app.route("/worker")
def worker_dashboard():
    user = current_user()
    if not user or user["role"]!="worker":
        return redirect(url_for("login"))
    return render_template_string(WORKER_HTML, username=user["username"])

# ---------------- Admin APIs ----------------
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

# ---------------- HTML Templates ----------------

LOGIN_HTML = """
<!doctype html><title>Login</title>
<h2>Login</h2>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post">
  Username: <input name="username" required><br>
  Password: <input name="password" type="password" required><br>
  <button type="submit">Login</button>
</form>
"""

ADMIN_HTML = """
<!doctype html><title>Admin</title>
<h2>Admin Dashboard: {{username}}</h2>
<a href="/logout">Logout</a>
<hr>
<h3>Add Worker / Shopkeeper</h3>
<form id="addUserForm">
  Username: <input id="new_username" required><br>
  Password: <input id="new_password" type="password" required><br>
  Role: <select id="new_role">
    <option value="worker">Worker</option>
    <option value="shopkeeper">Shopkeeper</option>
  </select><br>
  <button type="button" onclick="addUser()">Add User</button>
</form>
<div id="addUserResult"></div>

<h3>Change your password</h3>
<form id="changePassForm">
  Old Password: <input id="old_pass" type="password"><br>
  New Password: <input id="new_pass" type="password"><br>
  <button type="button" onclick="changePass()">Change Password</button>
</form>
<div id="changePassResult"></div>

<script>
async function addUser(){
  const username = document.getElementById("new_username").value;
  const password = document.getElementById("new_password").value;
  const role = document.getElementById("new_role").value;
  const r = await fetch("/admin/add_user",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({username,password,role})
  });
  const res = await r.json();
  document.getElementById("addUserResult").innerText = res.message || res.error;
}

async function changePass(){
  const old_password = document.getElementById("old_pass").value;
  const new_password = document.getElementById("new_pass").value;
  const r = await fetch("/user/change_password",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({old_password,new_password})
  });
  const res = await r.json();
  document.getElementById("changePassResult").innerText = res.message || res.error;
}
</script>
"""

SHOPKEEPER_HTML = """
<!doctype html><title>Shopkeeper</title>
<h2>Shopkeeper Dashboard: {{username}}</h2>
<a href="/logout">Logout</a>
<hr>
<h3>Settings</h3>
<form id="changePassForm">
  Old Password: <input id="old_pass" type="password"><br>
  New Password: <input id="new_pass" type="password"><br>
  <button type="button" onclick="changePass()">Change Password</button>
</form>
<div id="changePassResult"></div>

<script>
async function changePass(){
  const old_password = document.getElementById("old_pass").value;
  const new_password = document.getElementById("new_pass").value;
  const r = await fetch("/user/change_password",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({old_password,new_password})
  });
  const res = await r.json();
  document.getElementById("changePassResult").innerText = res.message || res.error;
}
</script>
"""

WORKER_HTML = """
<!doctype html><title>Worker</title>
<h2>Worker Dashboard: {{username}}</h2>
<a href="/logout">Logout</a>
<hr>
<h3>Settings</h3>
<form id="changePassForm">
  Old Password: <input id="old_pass" type="password"><br>
  New Password: <input id="new_pass" type="password"><br>
  <button type="button" onclick="changePass()">Change Password</button>
</form>
<div id="changePassResult"></div>

<script>
async function changePass(){
  const old_password = document.getElementById("old_pass").value;
  const new_password = document.getElementById("new_pass").value;
  const r = await fetch("/user/change_password",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({old_password,new_password})
  });
  const res = await r.json();
  document.getElementById("changePassResult").innerText = res.message || res.error;
}
</script>
"""

# ---------------- Run ----------------
if __name__=="__main__":
    app.run(debug=True, port=5000)
