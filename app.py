# app.py - Cleaned and corrected full application file
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_session import Session
from flask_login import LoginManager
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --------------- Config & App Setup ---------------
app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --------------- DB Connection Helper ---------------
def get_conn():
    # Update credentials if needed
    return psycopg2.connect(
        host="localhost",
        database="chilli_db",
        user="postgres",
        password="Dahdah@18012002"
    )


# --------------- Flask-Login loader ---------------
@login_manager.user_loader
def load_user(user_id):
    """
    Must return a user object (or None). We create a tiny object with get_id.
    NOTE: user_id may be a string from Flask-Login; convert as needed.
    """
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
    except Exception:
        return None

    if user:
        class UserObj:
            def __init__(self, id):
                self.id = id
            def is_authenticated(self): return True
            def is_active(self): return True
            def is_anonymous(self): return False
            def get_id(self): return str(self.id)

        return UserObj(user["user_id"])
    return None


# ------------------- Auth / Users -------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        company_name = request.form.get("company_name")
        short_name = request.form.get("short_name")
        gst = request.form.get("gst")
        pan = request.form.get("pan")
        mobile = request.form.get("mobile")
        adhar = request.form.get("adhar")
        bank_name = request.form.get("bank_name")
        account_number = request.form.get("account_number")
        ifsc_code = request.form.get("ifsc_code")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        # Basic validations
        if not (mobile and mobile.isdigit() and len(mobile) == 10):
            flash("Mobile number must be exactly 10 digits.", "danger")
            return redirect(url_for("register"))
        if not password or len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isupper() for c in password):
            flash("Password must be at least 8 characters, include a number & uppercase letter.", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO users (company_name, short_name, gst, pan, mobile, adhar, bank_name, account_number, ifsc_code, email,username, password, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (company_name, short_name, gst, pan, mobile, adhar, bank_name, account_number, ifsc_code, email, username ,hashed_password, datetime.utcnow()))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error registering user: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cur.fetchone()
        finally:
            cur.close()
            conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["company_name"] = user.get("company_name")
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


# ------------------- Dashboard -------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", Username=session.get("email"))


# ------------------- Accounts (farmers/purchasers) -------------------
@app.route("/accounts_home")
def accounts_home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("accounts_home.html")


@app.route("/accounts/add", methods=["GET", "POST"])
@app.route("/accounts/edit/<int:account_id>", methods=["GET", "POST"])
@app.route("/accounts/add", methods=["GET", "POST"])
@app.route("/accounts/edit/<int:account_id>", methods=["GET", "POST"])
def add_account(account_id=None):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    account = None
    right_side_accounts = []
    account_type = None

    # ---------- EDIT (GET) ----------
    

    # ---------- SAVE (POST) ----------
    if request.method == "POST":
        data = {k: request.form.get(k) for k in request.form}
        account_type = data.get("type")

        gst_value = data.get("gst")
        if account_type == "Farmer":
            gst_value = None
        elif account_type == "Purchaser" and not gst_value:
            flash("GST is required for Purchasers!", "danger")
            cur.close()
            conn.close()
            return redirect(request.referrer)

        # city_id handling
        city_id = None
        if data.get("city_id") and data.get("city_id") != "undefined":
            try:
                city_id = int(data.get("city_id"))
            except ValueError:
                pass

        try:
            if account_id:
                cur.execute("""
                    UPDATE accounts
                    SET type=%s, first_name=%s, middle_name=%s, last_name=%s,
                        adhar=%s, pan=%s, gst=%s, company_name=%s, short_name=%s,
                        account_name=%s, account_number=%s, bank_name=%s,
                        ifsc_code=%s, mobile=%s, email=%s, city_id=%s
                    WHERE account_id=%s AND user_id=%s
                """, (
                    account_type, data.get("first_name"), data.get("middle_name"),
                    data.get("last_name"), data.get("adhar"), data.get("pan"),
                    gst_value, data.get("company_name"), data.get("short_name"),
                    data.get("account_name"), data.get("account_number"),
                    data.get("bank_name"), data.get("ifsc_code"),
                    data.get("mobile"), data.get("email"),
                    city_id, account_id, session["user_id"]
                ))
                flash("Account updated successfully!", "success")
            else:
                cur.execute("""
                    INSERT INTO accounts (
                        type, first_name, middle_name, last_name, adhar, pan, gst,
                        company_name, short_name, account_name, account_number,
                        bank_name, ifsc_code, mobile, email, user_id, city_id
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    account_type, data.get("first_name"), data.get("middle_name"),
                    data.get("last_name"), data.get("adhar"), data.get("pan"),
                    gst_value, data.get("company_name"), data.get("short_name"),
                    data.get("account_name"), data.get("account_number"),
                    data.get("bank_name"), data.get("ifsc_code"),
                    data.get("mobile"), data.get("email"),
                    session["user_id"], city_id
                ))
                flash("Account added successfully!", "success")

            conn.commit()

        except Exception as e:
            conn.rollback()
            flash(str(e), "danger")

    # ---------- RIGHT SIDE LIST (GET + POST) --------

        cur.execute("""
            SELECT a.account_id, a.first_name, a.middle_name, a.last_name, a.mobile,
                c.city
            FROM accounts a
            LEFT JOIN cities c ON a.city_id = c.city_id
            WHERE a.type = %s AND a.user_id = %s AND a.city_id = %s
            ORDER BY city DESC
        """, (account_type, session["user_id"] , city_id))
    
        right_side_accounts = cur.fetchall()

        cur.close()
        conn.close()

    return render_template(
        "accounts_add.html",
        account=None if request.method == "POST" else account,
        right_side_accounts=right_side_accounts,

        account_type=account_type
    )


@app.route("/accounts/view/<account_type>")
def view_accounts(account_type):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    user_id = session["user_id"]
    right_side_accounts = []
   
    cur.execute("""
        SELECT a.account_id, a.type, a.first_name, a.middle_name, a.last_name,
               a.adhar, a.pan, a.gst, a.company_name, a.short_name,
               a.account_name, a.account_number, a.bank_name, a.ifsc_code,
               a.mobile, a.email, a.city_id, c.city, c.district
        FROM accounts a
        LEFT JOIN cities c ON a.city_id = c.city_id
        WHERE a.type = %s AND a.user_id = %s
        ORDER BY a.account_id DESC
    """, (account_type, user_id))
    accounts = cur.fetchall()
    cur.close()
    return render_template("view_accounts.html" , accounts=accounts, account_type=account_type)

# --------- Search Farmer and Purchaser --------------------------

@app.route("/accounts/search/<account_type>")
def search_accounts(account_type):
    if "user_id" not in session:
        return jsonify([])

    user_id = session["user_id"]
    search = request.args.get("q", "").strip().lower()
    account_type = account_type.capitalize()

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    search_term = f"%{search}%"

    cur.execute("""
       SELECT 
    a.account_id,
    a.first_name,
    a.middle_name,
    a.last_name,
    a.adhar,
    a.pan,
    a.account_name,
    a.account_number,
    a.bank_name,
    a.ifsc_code,
    c.district,
    c.city,
    a.mobile,
    a.email
FROM accounts a
LEFT JOIN cities c ON a.city_id = c.city_id
WHERE
            a.type = %s
            AND a.user_id = %s
            AND (
                LOWER(a.first_name) LIKE %s
                OR LOWER(a.last_name) LIKE %s
                OR a.mobile LIKE %s
                OR LOWER(c.city) LIKE %s
            )
        ORDER BY a.account_id DESC
        LIMIT 20
    """, (account_type, user_id, search_term, search_term, search_term, search_term))

    results = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(results)


#---------------- --- Edit Account -------------------
# @app.route("/edit_account/<int:account_id>")

# def edit_account(account_id):
#     if "user_id" not in session:
#         return redirect(url_for("login"))
    
#     user_id = session["user_id"]
#     conn = get_conn()

#     cur = conn.cursor()
#     cur.execute(
#     """ SELECT a.account_id, a.type, a.first_name, a.middle_name, a.last_name,
#                a.adhar, a.pan, a.gst, a.company_name, a.short_name,
#                a.account_name, a.account_number, a.bank_name, a.ifsc_code,
#                a.mobile, a.email, a.city_id, c.city, c.district
#                FROM accounts a 
#                LEFT JOIN cities c ON a.city_id = c.city_id
#                WHERE
#                a.user_id = %s AND a.account_id = %s """, 
#                ( user_id, account_id))
    
#     account = cur.fetchone()
    
#     cur.close()
#     conn.close()

#     if not account:
#         abort(404)
    


#     return redirect(url_for("add_account", account=account , edit=True))



@app.route('/delete_account/<int:account_id>')
def delete_account(account_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT type FROM accounts WHERE account_id=%s AND user_id=%s", (account_id, user_id))
    account = cur.fetchone()
    account_type = account[0] if account else "Farmer"
    cur.execute("DELETE FROM accounts WHERE account_id=%s AND user_id=%s", (account_id, user_id))
    conn.commit()
    cur.close()
    conn.close()
    flash(f"{account_type} deleted successfully!", "success")
    return redirect(url_for('view_accounts', account_type=account_type))


# ------------------- Cities + Helpers -------------------
@app.route("/cities", methods=["GET", "POST"])
def cities():
    conn = get_conn()
    cur = conn.cursor()
    if request.method == "POST":
        city = request.form.get("city")
        district = request.form.get("district")
        state = request.form.get("state")
        if city:
            try:
                cur.execute("INSERT INTO cities (city, district, state) VALUES (%s, %s, %s)", (city, district, state))
                conn.commit()
                flash(f"City '{city}' added successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding city: {str(e)}", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("cities"))
    cur.execute("SELECT city_id, city, district, state FROM cities ORDER BY city")
    cities_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("cities.html", cities=cities_list)


@app.route("/check_city")
def check_city():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"exists": False, "id": None})
    parts = name.split("—")
    city_name = parts[0].strip()
    district = parts[1].strip() if len(parts) > 1 else ""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT city_id FROM cities WHERE LOWER(city)=LOWER(%s) AND LOWER(district)=LOWER(%s)", (city_name, district))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"exists": bool(row), "id": row[0] if row else None})


@app.route("/check_farmer_exists")
def check_farmer_exists():
    city_id = request.args.get("city_id")
    name = request.args.get("name", "").strip().lower()
    if not city_id or not name:
        return jsonify({"exists": False})
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT account_id, first_name, middle_name, last_name
        FROM accounts
        WHERE city_id = %s AND type = 'Farmer'
    """, (city_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for row in rows:
        full_name = " ".join([part for part in row[1:] if part]).strip().lower()
        if full_name == name:
            return jsonify({"exists": True, "id": row[0]})
    return jsonify({"exists": False})


@app.route('/adding_city_ajax', methods=['POST'])
def adding_city_ajax():
    data = request.get_json()
    city_name = data.get("city")
    district = data.get("district")
    state = data.get("state")
    conn = get_conn()
    cur = conn.cursor()
    parts = city_name.split("-")
    city_name = parts[0].strip()
    district = parts[1].strip() if len(parts) > 1 else district.strip()
    cur.execute("SELECT city_id FROM cities WHERE LOWER(city) = LOWER(%s) AND LOWER (district) = LOWER(%s)", (city_name, district))
    existing = cur.fetchone()
    if existing:
        city_id = existing[0]
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "City already exists!", "city_id": city_id})
    cur.execute("INSERT INTO cities (city, district, state) VALUES (%s, %s, %s) RETURNING city_id", (city_name, district, state))
    city_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "city_name": city_name, "city_id": city_id})


# ------------------- Farmer list helper -------------------
@app.route("/farmers_list_by_city/<int:city_id>")
def farmers_list_by_city(city_id):
    q = request.args.get("q", "").strip().lower()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT account_id,
               TRIM(
                   COALESCE(first_name, '') || ' ' ||
                   COALESCE(middle_name, '') || ' ' ||
                   COALESCE(last_name, '')
               ) AS full_name
        FROM accounts
        WHERE city_id = %s
          AND LOWER(TRIM(type)) = 'farmer'
          AND LOWER(
                COALESCE(first_name, '') || ' ' ||
                COALESCE(middle_name, '') || ' ' ||
                COALESCE(last_name, '')
              ) LIKE %s
        ORDER BY full_name
        LIMIT 50
    """, (city_id, f"%{q}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"farmers": [{"id": r[0], "name": r[1]} for r in rows]})


# ------------------- Utility: next lot number per user+date -------------------
def compute_next_lot_number(conn, user_id, selected_date):
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(MAX(lot_number), 0) + 1
        FROM lots
        WHERE user_id = %s AND date = %s
    """, (user_id, selected_date))
    nxt = cur.fetchone()[0] or 1
    cur.close()
    return nxt


# @app.route("/get_next_lot")
# def get_next_lot():
#     if "user_id" not in session:
#         return jsonify({"next_number": 1})
#     user_id = session["user_id"]
#     selected_date_str = request.args.get("date")
#     try:
#         selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date() if selected_date_str else datetime.today().date()
#     except ValueError:
#         selected_date = datetime.today().date()
#     conn = get_conn()
#     next_number = compute_next_lot_number(conn, user_id, selected_date)
#     conn.close()
#     return jsonify({"next_number": next_number})


#------------------- Set Lot Date in Session -------------------

@app.route("/set_lot_date",methods=["POST"])
def set_lot_date():
    data = request.get_json()
    session["lot_date"] = data.get("date")
    return jsonify({"status": "success"})

#------------------- Get Current Lot Date from Session -------------------

@app.route("/get_current_date")
def get_current_date():
    return jsonify({
        "date": session.get("lot_date")
    })


# ------------------- LOTS (create / list / edit / delete) -------------------
@app.route("/lots", methods=["GET", "POST"])
def lots():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # POST - create a new lot
    if request.method == "POST":
        conn = get_conn()
        cur = conn.cursor()
        try:
            user_id = session.get("user_id")
            date = request.form.get("date")
            lot_number = request.form.get("lot_number")
            city_id = request.form.get("city_id")
            farmer_id = request.form.get("farmer_id")
            no_of_bags = request.form.get("no_of_bags")

            # compute lot_number if missing
            if not lot_number or str(lot_number).strip() == "":
                try:
                    selected_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.today().date()
                except Exception:
                    selected_date = datetime.today().date()
                lot_number = compute_next_lot_number(conn, user_id, selected_date)

            cur.execute("""
                INSERT INTO lots (user_id, date, lot_number, city_id, farmer_id, no_of_bags, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING lot_id
            """, (user_id, date, lot_number, city_id, farmer_id, no_of_bags))
            lot_id = cur.fetchone()[0]
            conn.commit()
            flash(f"✅ Lot {lot_number} saved successfully!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"⚠️ Error saving lot: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("lots"))

    # GET - show form and recent lots
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT city_id, city, district FROM cities ORDER BY district, city")
    cities = [{"id": c[0], "city": c[1], "district": c[2]} for c in cur.fetchall()]

    cur.execute("""
    SELECT 
        l.lot_id,
        l.lot_number, 
        l.date,
        c.city, 
        a.first_name || ' ' || COALESCE(a.middle_name, '') || ' ' || COALESCE(a.last_name, '') AS farmer_name,
        l.no_of_bags,
        l.rate,
        l.purchaser_id
    FROM lots l
    LEFT JOIN cities c ON l.city_id = c.city_id
    LEFT JOIN accounts a ON l.farmer_id = a.account_id
    WHERE l.user_id = %s AND l.date = %s
    ORDER BY l.lot_number DESC
    LIMIT 10
""", (session["user_id"], session.get("lot_date")))

    lots_list = cur.fetchall()
    cur.close()
    conn.close()

    lots_display = []
    for r in lots_list:
        lots_display.append({
            "lot_id": r[0],
            "lot_number": r[1],
            "date": r[2],
            "city": r[3],
            "farmer": r[4],
            "bags": r[5],
            "rate": r[6],
            "purchaser_id": r[7]
        })

    return render_template("lots.html", cities=cities, lots=lots_display)

@app.route("/get_next_lot")
def get_next_lot():
    lot_date = session.get("lot_date")

    if not lot_date:
        return jsonify(next_number=1)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(MAX(lot_number), 0)
        FROM lots
        WHERE date = %s
    """, (lot_date,))

    max_lot = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify(next_number=max_lot + 1)




@app.route("/edit_lot/<int:lot_id>", methods=["GET"])
def edit_lot(lot_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT lot_id, date, lot_number, city_id, farmer_id, no_of_bags, rate, purchaser_id
        FROM lots
        WHERE lot_id = %s AND user_id = %s
    """, (lot_id, session["user_id"]))
    lot = cur.fetchone()
    cur.close()
    conn.close()
    if not lot:
        flash("Lot not found!", "danger")
        return redirect(url_for("lots"))
    
    # Prepare farmers list for edit form
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(""" SELECT account_id, first_name || ' ' || COALESCE(middle_name, '') || ' ' || COALESCE(last_name, '') AS farmer_name
                from lots l
                LEFT JOIN accounts a ON l.farmer_id = a.account_id
                Where a.type = 'Farmer'
                order by farmer_name """
                )
    farmers = [{"id": a[0], "farmer_name": a[1]} for a in cur.fetchall()]
    cur.close()
    conn.close()

    # Prepare cities list for edit form
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT city_id, city, district FROM cities ORDER BY district, city")
    cities = [{"id": c[0], "city": c[1], "district": c[2]} for c in cur.fetchall()]
    cur.close()
    conn.close()

    return render_template("lots_edit.html", lot=lot, cities=cities , farmers=farmers)


@app.route("/update_lot/<int:lot_id>", methods=["POST"])
def update_lot(lot_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_conn()
    cur = conn.cursor()
    try:
        date = request.form.get("date")
        lot_number = request.form.get("lot_number")
        city_id = request.form.get("city_id")
        farmer_id = request.form.get("farmer_id")
        no_of_bags = request.form.get("no_of_bags")

        if not lot_number:
            cur.execute("SELECT lot_number FROM lots WHERE lot_id = %s", (lot_id,))
            row = cur.fetchone()
            lot_number = row[0] if row else None

        cur.execute("""
            UPDATE lots
            SET date = %s, lot_number = %s, city_id = %s, farmer_id = %s, no_of_bags = %s, updated_at = CURRENT_TIMESTAMP
            WHERE lot_id = %s AND user_id = %s
        """, (date, lot_number, city_id, farmer_id, no_of_bags, lot_id, session["user_id"]))
        conn.commit()
        flash(f"✅ Lot {lot_number} updated successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"⚠️ Error updating lot: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("lots"))


@app.route("/delete_lot/<int:lot_id>")
def delete_lot(lot_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM lots WHERE lot_id = %s AND user_id = %s", (lot_id, session["user_id"]))
        conn.commit()
        flash("🗑️ Lot deleted successfully!", "info")
    except Exception as e:
        conn.rollback()
        flash(f"⚠️ Error deleting lot: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("lots"))


#-------- Save the Lots -----------------------------
@app.route("/Save_lot", methods=["POST"])
def Save_lot():
    data = request.get_json()
    lot_date = session.get("lot_date")
    if not lot_date:
        return jsonify({"error": "Date is required"}), 400
    user_id = session.get("user_id")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO lots (user_id, date, lot_number, city_id, farmer_id, no_of_bags, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)RETURNING Lot_number
        """, (user_id, lot_date, data.get("lot_number"), data.get("city_id"), data.get("farmer_id"), data.get("no_of_bags")))
        saved_lot_number = cur.fetchone()[0]
        conn.commit()
        session["current_lot_number"] = saved_lot_number + 1

        return jsonify({
             "status": "ok",
            "saved_lot": {
                "lot_number": saved_lot_number,
                "date": lot_date,
                "city_id": data["city_id"],
                "farmer_id": data["farmer_id"],
                "bags": data["no_of_bags"]
            }

            
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500  
    finally:
        cur.close()
        conn.close()
#----------View Lots by Date ----------------------------

# @app.route("/View_lots_by_date", methods=["GET", "POST"])
# def View_lots_by_date():
#     lot_date = session.get("lot_date")

#     conn = get_conn()
#     cur = conn.cursor()

#     lots = []

#     if lot_date:
#         cur.execute("""
#             SELECT lot_id, lot_number, date, city, farmer, bags
#             FROM lots
#             WHERE date = %s
#             ORDER BY lot_number DESC
#             LIMIT 10
#         """, (lot_date,))

#         rows = cur.fetchall()

#         for r in rows:
#             lots.append({
#                 "lot_id": r[0],
#                 "lot_number": r[1],
#                 "date": r[2],
#                 "city": r[3],
#                 "farmer": r[4],
#                 "bags": r[5],
#             })

#     cur.close()
#     conn.close()

#     return render_template("lots.html", lots=lots)


# ------------------- AJAX / Rates Routes -------------------
@app.route("/get_cities")
def get_cities():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT city_id, city, district FROM cities ORDER BY district, city")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cities = [{"id": r[0], "city": r[1], "district": r[2]} for r in rows]
    return jsonify({"cities": cities})


@app.route("/rates")
def rates():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("rates.html")


@app.route("/get_lots_by_date")
def get_lots_by_date():
    date = request.args.get("date")
    user_id = session["user_id"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.lot_id, l.lot_number, 
               c.city, c.city_id,
               a.first_name || ' ' || COALESCE(a.middle_name,'') || ' ' || COALESCE(a.last_name,'') AS farmer,
               l.farmer_id,
               l.no_of_bags
        FROM lots l
        LEFT JOIN cities c ON c.city_id = l.city_id
        LEFT JOIN accounts a ON a.account_id = l.farmer_id
        WHERE l.user_id = %s AND l.date = %s
        ORDER BY l.lot_number
    """, (user_id, date))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    lots = []
    for r in rows:
        lots.append({
            "lot_id": r[0],
            "lot_number": r[1],
            "city": r[2],
            "city_id": r[3],
            "farmer": r[4],
            "farmer_id": r[5],
            "bags": r[6],
        })
    return jsonify({"lots": lots})

@app.route("/get_purchaser_for_rate" , methods=["GET"])
def get_purchaser_for_rate():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(""" SELECT account_id , short_name    FROM accounts WHERE type = 'Purchaser' 
                order by company_name """)
    rows = cur.fetchall()
    purchasers = []
    for row in rows:
        purchasers.append({
            "id": row[0],
            "short_name": row[1]
        })


    cur.close()
    conn.close()
        
    return jsonify(purchasers)



@app.route("/save_rate", methods=["POST"])
def save_rate():
    data = request.get_json()
    user_id = session.get("user_id")
    lot_id = data.get("lot_id")
    purchaser_id = data.get("purchaser_id")
    rate_value = data.get("rate")
    if not lot_id or not rate_value or not purchaser_id:
        return jsonify({"error": "lot_id, purchaser_id and rate are required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE lots
            SET rate = %s, purchaser_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE lot_id = %s AND user_id = %s
        """, (rate_value, purchaser_id, lot_id, user_id))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Lot not found or not authorized"}), 404
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500
    cur.close()
    conn.close()
    return jsonify({
    "status": "success",
    "message": "Rate saved to lot successfully!"
})


@app.route("/get_saved_rates")
def get_saved_rates():
    date = request.args.get("date")
    user_id = session["user_id"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            l.lot_id,
            l.lot_number,
            a.first_name || ' ' || COALESCE(a.middle_name,'') || ' ' || COALESCE(a.last_name,'') AS farmer,
            l.no_of_bags,
            l.rate,
            p.account_id,
            p.company_name,
            p.first_name || ' ' || COALESCE(p.middle_name,'') || ' ' || COALESCE(p.last_name,'') AS purchaser_name
        FROM lots l
        LEFT JOIN accounts a ON a.account_id = l.farmer_id
        LEFT JOIN accounts p ON p.account_id = l.purchaser_id
        WHERE l.date = %s AND l.user_id = %s AND l.rate IS NOT NULL
        ORDER BY l.lot_number
    """, (date, user_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    saved = []
    for r in rows:
        saved.append({
            "lot_id": r[0],
            "lot_number": r[1],
            "farmer": r[2],
            "bags": r[3],
            "rate_value": r[4],
            "purchaser_id": r[5],
            "purchaser_company": r[6] or "",
            "purchaser_name": r[7] or ""
        })
    return jsonify({"saved": saved})


@app.route("/purchasers_search")
def purchasers_search():
    q = request.args.get("q", "").strip().lower()
    user_id = session.get("user_id")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT account_id, COALESCE(company_name, '') AS company_name,
               COALESCE(first_name,'') || ' ' || COALESCE(middle_name,'') || ' ' || COALESCE(last_name,'') AS full_name
        FROM accounts
        WHERE user_id = %s AND LOWER(type) = 'purchaser' AND (
            LOWER(COALESCE(company_name,'')) LIKE %s OR
            LOWER(COALESCE(first_name,'')) LIKE %s OR
            LOWER(COALESCE(last_name,'')) LIKE %s
        )
        ORDER BY company_name NULLS LAST, full_name
        LIMIT 50
    """, (user_id, f"%{q}%", f"%{q}%", f"%{q}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    results = []
    for r in rows:
        display = r[1] if r[1] and r[1].strip() != "" else (r[2].strip() or "Unnamed")
        results.append({"id": r[0], "name": display})
    return jsonify({"purchasers": results})


# ------------------- Rates (legacy) - keep placeholder or remove if not used ---------------
@app.route("/add_rate", methods=["GET","POST"])
def add_rate():
    # kept for compatibility with earlier UI link; actual rate-saving uses /save_rate and updates lots.
    if request.method == "POST":
        product_name = request.form.get("product_name")
        rate = request.form.get("rate")
        effective_date = request.form.get("effective_date")
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO rates (product_name, rate, effective_date) VALUES (%s, %s, %s)", (product_name, rate, effective_date))
            conn.commit()
            flash("Rate added successfully!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error adding rate: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("rates"))
    return render_template("rates_add.html")
#-------------------- WEIGHTS OF EACH BAGS  --------------------

@app.route("/weights")
def weights():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("weights.html")


#------------- GETS THE LOTS BY DATE -----------------------------
@app.route("/get_all_lots_of_date")
def get_all_lots_of_date():
    date = request.args.get("date")
    user_id = session.get("user_id")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT 
                l.Lot_id ,
                 l.Lot_number , 
                l.no_of_bags ,
                l.rate,
                c.city,

                a.first_name || ' ' || COALESCE(a.middle_name,'') || ' ' || COALESCE(a.last_name,'') AS farmer,
                CASE
                WHEN p.company_name IS NOT NULL AND p.company_name <> '' THEN
                    p.company_name ||
                    CASE WHEN p.short_name IS NOT NULL AND p.short_name <> '' 
                         THEN ' (' || p.short_name || ')'
                         ELSE '' 
                    END
                ELSE p.short_name
            END AS purchaser
                from lots l
                JOIN accounts a ON l.farmer_id = a.account_id 
                JOIN accounts p ON l.purchaser_id = p.account_id
                JOIN cities c ON l.city_id = c.city_id
                WHERE l.user_id = %s AND l.date = %s
                order by l.lot_number""", (user_id, date))

    

    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    lots = []
    for r in rows:
        lots.append({
            "lot_id":r[0],
            "lot_number": r[1],
            "bags":r[2],
            "rate":r[3],
            "city":r[4],
            "farmer":r[5],
            "purchaser":r[6]


        })
    return jsonify({"lots": lots})

#------------------- SAVE WEIGHT OF EACH BAG -----------------------           
@app.route("/save_weight", methods=["POST"])
def save_weight():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    lot_id = data.get("lot_id")
    weights = data.get("weights", [])

    if not lot_id:
        return jsonify({"error": "lot_id is required"}), 400

    if not weights or not isinstance(weights, list):
        return jsonify({"error": "weights list required"}), 400

    user_id = session.get("user_id")
    total_weight = sum([float(w) for w in weights if w not in (None, "", " ")])

    conn = get_conn()
    cur = conn.cursor()

    try:
        # 1️⃣ Delete old weights (if editing)
        cur.execute("DELETE FROM bag_weights WHERE lot_id = %s AND user_id = %s",
                    (lot_id, user_id))
        
        cur.execute("SELECT farmer_id, purchaser_id FROM lots WHERE lot_id = %s AND user_id = %s",
                    (lot_id, user_id))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Lot {lot_id} not found for user.")
        farmer_id, purchaser_id = row
            

        # 2️⃣ Insert new weights
        for i, w in enumerate(weights, start=1):
            cur.execute("""
                INSERT INTO bag_weights (lot_id, user_id, bag_no, weight,farmer_id , purchaser_id ,  created_at)
                VALUES (%s, %s, %s, %s,%s,%s, CURRENT_TIMESTAMP)
            """, (lot_id, user_id, i, w , farmer_id , purchaser_id))

        # 3️⃣ Update total weight in lots table
        cur.execute("""
            UPDATE lots
            SET total_weight = %s, updated_at = CURRENT_TIMESTAMP
            WHERE lot_id = %s AND user_id = %s
        """, (total_weight, lot_id, user_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "Weights saved successfully!", "total_weight": total_weight})



# ------------------- 1 / Tax / Admin -------------------
# @app.route("/billing")
# def billing():
#     conn = get_conn()
#     cur = conn.cursor()
#     # NOTE: this query assumes your billing table & users table fields; adjust if needed.
#     cur.execute("""
#         SELECT b.bill_id, b.bill_date, u.company_name, b.lot_no, b.total_amount, b.paid
#         FROM billing b
#         JOIN users u ON u.user_id = b.account_id
#         ORDER BY b.bill_date DESC
#     """)
#     bills = cur.fetchall()
#     cur.close()
#     conn.close()
#     return render_template("billing.html", bills=bills, title="Billing")


# @app.route("/add_bill", methods=["GET", "POST"])
# def add_bill():
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT user_id, company_name FROM users ORDER BY company_name")
#     accounts = cur.fetchall()
#     cur.close()
#     conn.close()

#     if request.method == "POST":
#         account_id = request.form.get("account_id")
#         lot_no = request.form.get("lot_no")
#         bill_date = request.form.get("bill_date")
#         total_amount = request.form.get("total_amount")
#         conn = get_conn()
#         cur = conn.cursor()
#         try:
#             cur.execute("INSERT INTO billing (bill_date, account_id, lot_no, total_amount) VALUES (%s,%s,%s,%s)", (bill_date, account_id, lot_no, total_amount))
#             conn.commit()
#             flash("Bill added successfully!", "success")
#         except Exception as e:
#             conn.rollback()
#             flash(f"Error adding bill: {str(e)}", "danger")
#         finally:
#             cur.close()
#             conn.close()
#         return redirect(url_for("billing"))
#     return render_template("billing_add.html", accounts=accounts)


# @app.route("/tax")
# def tax():
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM tax ORDER BY tax_name")
#     taxes = cur.fetchall()
#     cur.close()
#     conn.close()
#     return render_template("tax.html", taxes=taxes, title="Tax")


# @app.route("/add_tax", methods=["GET", "POST"])
# def add_tax():
#     if request.method == "POST":
#         tax_name = request.form.get("tax_name")
#         rate = request.form.get("rate")
#         description = request.form.get("description", "")
#         conn = get_conn()
#         cur = conn.cursor()
#         try:
#             cur.execute("INSERT INTO tax (tax_name, rate, description) VALUES (%s,%s,%s)", (tax_name, rate, description))
#             conn.commit()
#             flash("Tax added successfully!", "success")
#         except Exception as e:
#             conn.rollback()
#             flash(f"Error adding tax: {str(e)}", "danger")
#         finally:
#             cur.close()
#             conn.close()
#         return redirect(url_for("tax"))
#     return render_template("tax_add.html")


# @app.route("/admin_panel")
# def admin_panel():
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT COUNT(*) FROM users")
#     total_users = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM accounts")
#     total_accounts = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM lots")
#     total_lots = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM billing")
#     total_bills = cur.fetchone()[0]
#     cur.close()
#     conn.close()
#     return render_template("admin_panel.html", username=session.get("email", "Admin"),
#                            total_users=total_users, total_accounts=total_accounts,
#                            total_lots=total_lots, total_bills=total_bills)


# ------------------- Run -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
