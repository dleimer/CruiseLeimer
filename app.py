from flask import Flask, render_template, request, jsonify
import sqlite3, os
from datetime import datetime

app = Flask(__name__)

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'cruise.db'))

# Ensure the directory exists (needed when Render disk is mounted at /data)
_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

CATEGORIES = ['Documents & IDs', 'Bookings', 'Getting There', 'Packing', 'Day of Departure']
COST_CATEGORIES = ['Hotel', 'Parking', 'Transport', 'Excursion', 'Other']


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            category   TEXT NOT NULL,
            text       TEXT NOT NULL,
            completed  INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS costs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount      REAL NOT NULL,
            category    TEXT DEFAULT 'General',
            notes       TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


init_db()


@app.route('/')
def index():
    return render_template('index.html',
                           categories=CATEGORIES,
                           cost_categories=COST_CATEGORIES)


@app.route('/api/data')
def api_data():
    conn = get_db()
    tasks = [dict(r) for r in conn.execute(
        "SELECT * FROM tasks ORDER BY category, created_at"
    ).fetchall()]
    costs = [dict(r) for r in conn.execute(
        "SELECT * FROM costs ORDER BY created_at DESC"
    ).fetchall()]
    conn.close()
    return jsonify({'tasks': tasks, 'costs': costs})


@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    text = data.get('text', '').strip()
    category = data.get('category', '').strip()
    if not text or not category:
        return jsonify({'error': 'missing fields'}), 400
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (category, text) VALUES (?, ?)", (category, text)
    )
    task_id = cur.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return jsonify(row)


@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET completed = CASE WHEN completed=1 THEN 0 ELSE 1 END WHERE id=?",
        (task_id,)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return jsonify(row)


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/costs', methods=['POST'])
def add_cost():
    data = request.json
    description = data.get('description', '').strip()
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return jsonify({'error': 'invalid amount'}), 400
    if not description or amount <= 0:
        return jsonify({'error': 'missing fields'}), 400
    category = data.get('category', 'Other').strip()
    notes = data.get('notes', '').strip()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO costs (description, amount, category, notes) VALUES (?,?,?,?)",
        (description, amount, category, notes)
    )
    cost_id = cur.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM costs WHERE id=?", (cost_id,)).fetchone())
    conn.close()
    return jsonify(row)


@app.route('/api/costs/<int:cost_id>', methods=['DELETE'])
def delete_cost(cost_id):
    conn = get_db()
    conn.execute("DELETE FROM costs WHERE id=?", (cost_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True, port=5006, host='0.0.0.0')
