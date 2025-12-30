import logging
logging.basicConfig(level=logging.INFO)
from flask import Flask, request, render_template, jsonify, send_file
import pandas as pd
import joblib
import os
import sqlite3
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from fpdf import FPDF


# PATH SETUP

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DB_PATH = os.path.join(BASE_DIR, "customer_segments.db")


# FLASK APP

app = Flask(__name__, template_folder=TEMPLATE_DIR)


# RATE LIMITING

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)


# API KEY SECURITY

API_KEY = os.getenv("API_KEY")

def require_api_key(req):
    return req.headers.get("X-API-KEY") == API_KEY


# LOAD MODEL & SCALER

scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
kmeans = joblib.load(os.path.join(MODEL_DIR, "customer_segmentation.pkl"))

FEATURES = ["Income", "Age", "Total_Spending", "Recency"]


# PERSONAS

PERSONAS = {
    0: {
        "name": "Budget Active Shoppers",
        "description": "Low-income customers who make small but frequent purchases.",
        "key_traits": ["Price sensitive", "Engaged", "Discount driven"],
        "business_strategy": ["Discount offers", "Low-cost bundles"]
    },
    1: {
        "name": "Premium Loyalists",
        "description": "High-income, high-spending customers.",
        "key_traits": ["High value", "Brand loyal"],
        "business_strategy": ["Loyalty rewards", "Premium offers"]
    },
    2: {
        "name": "At-Risk Customers",
        "description": "Low spending and high inactivity.",
        "key_traits": ["Churn risk", "Low engagement"],
        "business_strategy": ["Re-engagement campaigns"]
    },
    3: {
        "name": "Loyal Seniors",
        "description": "Older customers with stable behavior.",
        "key_traits": ["Stable", "Trust-based"],
        "business_strategy": ["Retention rewards"]
    }
}


# INPUT VALIDATION

def validate_inputs(income, age, spending, recency):
    if age < 18 or age > 100:
        return "Age must be between 18 and 100."
    if income <= 0:
        return "Income must be greater than 0."
    if spending < 0:
        return "Total spending cannot be negative."
    if recency < 0 or recency > 365:
        return "Recency must be between 0 and 365 days."
    return None


# DATABASE HELPERS

def save_prediction(income, age, spending, recency, cluster, persona):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO predictions
        (income, age, total_spending, recency, cluster, persona)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (income, age, spending, recency, cluster, persona))
    conn.commit()
    conn.close()

def fetch_history(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT income, age, total_spending, recency, cluster, persona, created_at
        FROM predictions
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# FRONTEND ROUTE

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")



# API: PREDICT

@app.route("/api/predict", methods=["POST"])
#@limiter.limit("10 per minute")
def api_predict():
    # if not require_api_key(request):
    #     return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    for key in FEATURES:
        if key not in data:
            return jsonify({"error": f"Missing {key}"}), 400

    income = data["Income"]
    age = data["Age"]
    spending = data["Total_Spending"]
    recency = data["Recency"]

    error = validate_inputs(income, age, spending, recency)
    if error:
        return jsonify({"error": error}), 400

    df = pd.DataFrame([[income, age, spending, recency]], columns=FEATURES)
    scaled = scaler.transform(df)
    cluster = int(kmeans.predict(scaled)[0])
    persona = PERSONAS[cluster]

    save_prediction(income, age, spending, recency, cluster, persona["name"])

    return jsonify({
        "cluster": cluster,
        "persona": persona["name"],
        "description": persona["description"],
        "strategy": persona["business_strategy"]
    })



# API: HISTORY
@app.route("/api/history", methods=["GET"])
def api_history():
    if not require_api_key(request):
        return jsonify({"error": "Unauthorized"}), 401

    rows = fetch_history()
    return jsonify([
        {
            "income": r[0],
            "age": r[1],
            "spending": r[2],
            "recency": r[3],
            "cluster": r[4],
            "persona": r[5],
            "timestamp": r[6]
        } for r in rows
    ])


# PDF EXPORT

@app.route("/download_report/<persona>")
def download_report(persona):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, f"Customer Persona Report", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Persona: {persona}", ln=True)

    pdf.output("report.pdf")
    return send_file("report.pdf", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
