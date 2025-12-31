from flask import Flask, request, render_template, jsonify, send_file
import pandas as pd
import joblib
import sqlite3
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from fpdf import FPDF
import os

# ---------------------------
# PATHS
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
DB_PATH = os.path.join(BASE_DIR, "customer_segments.db")
MODEL_DIR = os.path.join(BASE_DIR, "models")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# ---------------------------
# RATE LIMITING
# ---------------------------
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)

API_KEY = os.getenv("API_KEY")

def require_api_key(req):
    return req.headers.get("X-API-KEY") == API_KEY


# ---------------------------
# LOAD MODEL + SCALER
# ---------------------------
scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
kmeans = joblib.load(os.path.join(MODEL_DIR, "customer_segmentation.pkl"))

# must match training
FEATURES = ["Income", "Age", "Total_Spending", "Recency"]


# ---------------------------
# DB SETUP
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            income REAL,
            age INTEGER,
            total_spending REAL,
            recency INTEGER,
            cluster INTEGER,
            persona TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ---------------------------
# PERSONAS
# ---------------------------
PERSONAS = {
    0: {
        "name": "Budget Active Shoppers",
        "description": "Low-income customers who make small but frequent purchases.",
        "business_strategy": ["Discount offers", "Low-cost bundles"]
    },
    1: {
        "name": "Premium Loyalists",
        "description": "High-income, high-spending customers.",
        "business_strategy": ["Loyalty rewards", "Premium offers"]
    },
    2: {
        "name": "At-Risk Customers",
        "description": "Low spending and high inactivity.",
        "business_strategy": ["Re-engagement campaigns"]
    },
    3: {
        "name": "Loyal Seniors",
        "description": "Older customers with stable behavior.",
        "business_strategy": ["Retention rewards"]
    }
}


# ---------------------------
# VALIDATION (REALISTIC RANGES)
# ---------------------------
def validate_inputs(income, age, spending, recency):

    # match real dataset scale — prevents nonsense values
    if not 10000 <= income <= 120000:
        return "Income should be between 10,000 and 120,000."

    if not 18 <= age <= 100:
        return "Age must be between 18 and 100."

    if not 0 <= spending <= 5000:
        return "Total spending should be between 0 and 5,000."

    if not 0 <= recency <= 120:
        return "Recency should be between 0 and 120 days."

    return None


# ---------------------------
# DB SAVE
# ---------------------------
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


# ---------------------------
# ROUTES
# ---------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/api/predict", methods=["POST"])
def api_predict():
    try:
        data = request.get_json()

        for key in FEATURES:
            if key not in data:
                return jsonify({"error": f"Missing {key}"}), 400

        # numeric conversion
        income = float(data["Income"])
        age = int(float(data["Age"]))
        spending = float(data["Total_Spending"])
        recency = int(float(data["Recency"]))

        # validate user inputs
        error = validate_inputs(income, age, spending, recency)
        if error:
            return jsonify({"error": error}), 400

        df = pd.DataFrame(
            [[income, age, spending, recency]],
            columns=FEATURES
        )

        # DEBUG (optional): see what model receives
        print("\nINPUT TO MODEL:")
        print(df)

        scaled = scaler.transform(df)
        cluster = int(kmeans.predict(scaled)[0])

        persona = PERSONAS.get(cluster, {"name": "Unknown", "description": ""})

        save_prediction(income, age, spending, recency, cluster, persona["name"])

        return jsonify({
            "cluster": cluster,
            "persona": persona["name"],
            "description": persona["description"],
            "strategy": persona["business_strategy"]
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/api/history", methods=["GET"])
def api_history():
    if not require_api_key(request):
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT income, age, total_spending, recency, cluster, persona, created_at
        FROM predictions
        ORDER BY created_at DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()

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


@app.route("/download_report/<persona>")
def download_report(persona):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "Customer Persona Report", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Persona: {persona}", ln=True)

    filename = "report.pdf"
    pdf.output(filename)

    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
