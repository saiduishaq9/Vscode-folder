from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request, send_file

app = Flask(__name__, static_url_path="", static_folder=".")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "admissions.db"


def get_db_connection():
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicantId TEXT UNIQUE,
            fullName TEXT NOT NULL,
            dob TEXT NOT NULL,
            classLevel TEXT NOT NULL,
            phone TEXT NOT NULL,
            guardian TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            status TEXT NOT NULL,
            decision TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    connection.close()


def build_applicant_id():
    connection = get_db_connection()
    row = connection.execute(
        "SELECT applicantId FROM applications WHERE applicantId LIKE 'BHR-%' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    connection.close()

    if not row:
        return "BHR-2026-0001"

    current = row["applicantId"].split("-")[-1]
    try:
        number = int(current)
    except ValueError:
        number = 0
    return f"BHR-2026-{number + 1:04d}"


def load_applications():
    connection = get_db_connection()
    rows = connection.execute(
        "SELECT id, applicantId, fullName, dob, classLevel, phone, guardian, email, address, status, decision, created_at FROM applications ORDER BY id DESC"
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def save_application(payload):
    application = {
        "applicantId": build_applicant_id(),
        "fullName": payload["fullName"].strip(),
        "dob": payload["dob"],
        "classLevel": payload["classLevel"].strip(),
        "phone": payload["phone"].strip(),
        "guardian": payload["guardian"].strip(),
        "email": payload["email"].strip(),
        "address": payload["address"].strip(),
        "status": "Submitted",
        "decision": "Pending review"
    }

    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO applications (
            applicantId, fullName, dob, classLevel, phone, guardian, email, address, status, decision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            application["applicantId"],
            application["fullName"],
            application["dob"],
            application["classLevel"],
            application["phone"],
            application["guardian"],
            application["email"],
            application["address"],
            application["status"],
            application["decision"],
        ),
    )
    connection.commit()
    connection.close()
    return application


@app.route("/")
def index():
    return send_file(BASE_DIR / "index.html")


@app.route("/admin")
def admin_page():
    return send_file(BASE_DIR / "admin.html")


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "message": "Admissions backend is running."})


@app.route("/api/applications", methods=["GET", "POST"])
def applications():
    if request.method == "GET":
        return jsonify(load_applications())

    payload = request.get_json(silent=True) or {}
    required_fields = ["fullName", "dob", "classLevel", "phone", "guardian", "email", "address"]
    missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing:
        return jsonify({"success": False, "message": "Please complete all required application fields."}), 400

    application = save_application(payload)
    return jsonify({
        "success": True,
        "message": f"Application received for {application['fullName']}. Your applicant ID is {application['applicantId']}.",
        "applicantId": application["applicantId"]
    })


@app.route("/api/results", methods=["POST"])
def results():
    payload = request.get_json(silent=True) or {}
    applicant_id = str(payload.get("applicantId", "")).strip().upper()
    if not applicant_id:
        return jsonify({"success": False, "message": "Please provide an applicant ID."}), 400

    connection = get_db_connection()
    row = connection.execute(
        "SELECT fullName, decision, applicantId FROM applications WHERE applicantId = ?",
        (applicant_id,),
    ).fetchone()
    connection.close()

    if row:
        return jsonify({
            "success": True,
            "message": f"Result found for {row['fullName']}: {row['decision']}.",
            "applicantId": row["applicantId"],
            "status": row["decision"]
        })

    return jsonify({
        "success": False,
        "message": "No result found for that applicant ID. Please confirm the code and try again."
    }), 404


@app.route("/api/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not email or not password:
        return jsonify({"success": False, "message": "Please enter both email and password."}), 400

    if email.lower() == "admin@alimbukhary.edu.ng" and password == "admin123":
        return jsonify({
            "success": True,
            "message": "Welcome back! Admin access granted.",
            "role": "admin",
            "redirect": "/admin"
        })

    return jsonify({
        "success": True,
        "message": f"Welcome back! {email} has been authorized to access the applicant portal.",
        "user": email,
        "role": "applicant"
    })


@app.route("/api/admin/applications", methods=["GET"])
def admin_applications():
    return jsonify(load_applications())


@app.route("/api/admin/applications/<int:application_id>/decision", methods=["POST"])
def update_application_decision(application_id):
    payload = request.get_json(silent=True) or {}
    decision = str(payload.get("decision", "")).strip().title()
    if decision not in {"Accepted", "Rejected", "Pending Review"}:
        return jsonify({"success": False, "message": "Decision must be Accepted, Rejected, or Pending Review."}), 400

    connection = get_db_connection()
    cursor = connection.execute(
        "UPDATE applications SET decision = ?, status = ? WHERE id = ?",
        (decision, "Reviewed" if decision != "Pending Review" else "Submitted", application_id),
    )
    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        return jsonify({"success": False, "message": "Application not found."}), 404

    return jsonify({"success": True, "message": f"Application decision updated to {decision}."})


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
