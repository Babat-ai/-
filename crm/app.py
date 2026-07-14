import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "customers.db"

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with open(BASE_DIR / "schema.sql") as f:
            db.executescript(f.read())
        db.commit()


@app.route("/")
def index():
    db = get_db()
    customers = db.execute(
        "SELECT * FROM customers ORDER BY id DESC"
    ).fetchall()
    return render_template("index.html", customers=customers)


@app.route("/new", methods=["GET", "POST"])
def new_customer():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO customers (company_name, contact_name, email, phone, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                request.form["company_name"],
                request.form["contact_name"],
                request.form["email"],
                request.form["phone"],
                request.form["notes"],
            ),
        )
        db.commit()
        return redirect(url_for("index"))
    return render_template("form.html", customer=None)


@app.route("/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    db = get_db()
    if request.method == "POST":
        db.execute(
            "UPDATE customers SET company_name = ?, contact_name = ?, email = ?, "
            "phone = ?, notes = ? WHERE id = ?",
            (
                request.form["company_name"],
                request.form["contact_name"],
                request.form["email"],
                request.form["phone"],
                request.form["notes"],
                customer_id,
            ),
        )
        db.commit()
        return redirect(url_for("index"))
    customer = db.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return render_template("form.html", customer=customer)


@app.route("/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
