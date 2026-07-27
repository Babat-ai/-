import secrets
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "taskboard.db"

DEFAULT_CATEGORIES = ["やりたいこと", "やるべきこと", "よくわからないけどやらなきゃいけないこと"]
VALID_COLORS = {"yellow", "pink", "blue", "green", "orange", "purple"}

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


def get_category_or_404(category_id):
    db = get_db()
    category = db.execute(
        "SELECT * FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if category is None:
        abort(404)
    return category


def note_to_dict(note):
    return {
        "id": note["id"],
        "category_id": note["category_id"],
        "text": note["text"],
        "color": note["color"],
        "position": note["position"],
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
    for position, name in enumerate(DEFAULT_CATEGORIES):
        db.execute(
            "INSERT INTO categories (board_id, name, position) VALUES (?, ?, ?)",
            (board_id, name, position),
        )
    db.commit()
    return redirect(url_for("view_board", board_id=board_id))


@app.route("/board/<board_id>")
def view_board(board_id):
    board = get_board_or_404(board_id)
    db = get_db()
    categories = db.execute(
        "SELECT * FROM categories WHERE board_id = ? ORDER BY position, id",
        (board_id,),
    ).fetchall()
    notes = db.execute(
        """
        SELECT notes.* FROM notes
        JOIN categories ON categories.id = notes.category_id
        WHERE categories.board_id = ?
        ORDER BY notes.position, notes.id
        """,
        (board_id,),
    ).fetchall()

    notes_by_category = {}
    for note in notes:
        notes_by_category.setdefault(note["category_id"], []).append(note)

    return render_template(
        "board.html",
        board=board,
        categories=categories,
        notes_by_category=notes_by_category,
        colors=sorted(VALID_COLORS),
    )


@app.route("/api/boards/<board_id>/categories", methods=["POST"])
def add_category(board_id):
    get_board_or_404(board_id)
    name = (request.json or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM categories WHERE board_id = ?",
        (board_id,),
    ).fetchone()
    cur = db.execute(
        "INSERT INTO categories (board_id, name, position) VALUES (?, ?, ?)",
        (board_id, name, row["next_pos"]),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "name": name, "position": row["next_pos"]})


@app.route("/api/categories/<int:category_id>", methods=["PATCH"])
def rename_category(category_id):
    get_category_or_404(category_id)
    name = (request.json or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    db = get_db()
    db.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    db.commit()
    return jsonify({"id": category_id, "name": name})


@app.route("/api/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    get_category_or_404(category_id)
    db = get_db()
    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/categories/<int:category_id>/notes", methods=["POST"])
def add_note(category_id):
    get_category_or_404(category_id)
    data = request.json or {}
    text = data.get("text", "").strip()
    color = data.get("color", "yellow")
    if not text:
        return jsonify({"error": "text is required"}), 400
    if color not in VALID_COLORS:
        color = "yellow"
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM notes WHERE category_id = ?",
        (category_id,),
    ).fetchone()
    cur = db.execute(
        "INSERT INTO notes (category_id, text, color, position) VALUES (?, ?, ?, ?)",
        (category_id, text, color, row["next_pos"]),
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
    db.execute(
        "UPDATE notes SET text = ?, color = ? WHERE id = ?",
        (text, color, note_id),
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


@app.route("/api/categories/<int:category_id>/reorder", methods=["POST"])
def reorder_notes(category_id):
    get_category_or_404(category_id)
    note_ids = (request.json or {}).get("order", [])
    db = get_db()
    for position, note_id in enumerate(note_ids):
        db.execute(
            "UPDATE notes SET category_id = ?, position = ? WHERE id = ?",
            (category_id, position, note_id),
        )
    db.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
