import secrets
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "taskboard.db"

VALID_COLORS = {"yellow", "pink", "blue", "green", "orange", "purple"}
STARTER_NOTE = "ここにやりたいこと・やるべきことを書き出そう。付箋の「+」でサブタスクを線でつなげられるよ。"

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
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


def get_board_or_404(board_id):
    db = get_db()
    board = db.execute("SELECT * FROM boards WHERE id = ?", (board_id,)).fetchone()
    if board is None:
        abort(404)
    return board


def note_to_dict(note):
    return {
        "id": note["id"],
        "board_id": note["board_id"],
        "parent_id": note["parent_id"],
        "text": note["text"],
        "color": note["color"],
        "x": note["x"],
        "y": note["y"],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/board/new", methods=["POST"])
def new_board():
    db = get_db()
    board_id = secrets.token_urlsafe(8)
    db.execute(
        "INSERT INTO boards (id, name) VALUES (?, ?)", (board_id, "マイタスクボード")
    )
    db.execute(
        "INSERT INTO notes (board_id, parent_id, text, color, x, y) "
        "VALUES (?, NULL, ?, 'yellow', 200, 160)",
        (board_id, STARTER_NOTE),
    )
    db.commit()
    return redirect(url_for("view_board", board_id=board_id))


@app.route("/board/<board_id>")
def view_board(board_id):
    board = get_board_or_404(board_id)
    db = get_db()
    notes = db.execute(
        "SELECT * FROM notes WHERE board_id = ? ORDER BY id", (board_id,)
    ).fetchall()
    return render_template(
        "board.html",
        board=board,
        notes=[note_to_dict(n) for n in notes],
        colors=sorted(VALID_COLORS),
    )


@app.route("/api/boards/<board_id>/notes", methods=["POST"])
def add_note(board_id):
    get_board_or_404(board_id)
    data = request.json or {}
    text = data.get("text", "").strip()
    color = data.get("color", "yellow")
    if color not in VALID_COLORS:
        color = "yellow"
    x = float(data.get("x", 0))
    y = float(data.get("y", 0))
    parent_id = data.get("parent_id")

    db = get_db()
    if parent_id is not None:
        parent = db.execute(
            "SELECT * FROM notes WHERE id = ? AND board_id = ?", (parent_id, board_id)
        ).fetchone()
        if parent is None:
            return jsonify({"error": "parent not found"}), 400

    cur = db.execute(
        "INSERT INTO notes (board_id, parent_id, text, color, x, y) VALUES (?, ?, ?, ?, ?, ?)",
        (board_id, parent_id, text, color, x, y),
    )
    db.commit()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(note_to_dict(note))


@app.route("/api/notes/<int:note_id>", methods=["PATCH"])
def update_note(note_id):
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if note is None:
        abort(404)
    data = request.json or {}
    text = data.get("text", note["text"])
    color = data.get("color", note["color"])
    if color not in VALID_COLORS:
        color = note["color"]
    x = float(data.get("x", note["x"]))
    y = float(data.get("y", note["y"]))
    db.execute(
        "UPDATE notes SET text = ?, color = ?, x = ?, y = ? WHERE id = ?",
        (text, color, x, y, note_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return jsonify(note_to_dict(updated))


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if note is None:
        abort(404)
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001, host="0.0.0.0")
