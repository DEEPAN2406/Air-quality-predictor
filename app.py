from flask import Flask, render_template, request, redirect, session
import mysql.connector
from model import predict_aqi
from model import (
    get_accuracy, predict_all, get_best_algorithm,
    get_aqi_category, get_aqi_color, get_health_advice, get_dos_donts
)
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "airquality"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="air_quality_db"
)
cursor = db.cursor()

@app.route('/')
def index():
    return render_template("index.html")

# ---------- REGISTER ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        cursor.execute(
            "INSERT INTO users VALUES(NULL,%s,%s,%s)",
            (request.form['name'],request.form['email'],request.form['password'])
        )
        db.commit()
        return redirect('/login')
    return render_template("register.html")

# ---------- LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (request.form['email'],request.form['password'])
        )
        user = cursor.fetchone()
        if user:
            session['user'] = user[0]
            session['username'] = user[1]
            return redirect('/dashboard')
    return render_template("login.html")

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")

# ---------- AQI PREDICTION ----------

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    results = None
    accuracy = get_accuracy()
    best_algo = None
    best_aqi = None
    category = None
    color = None
    advice = None
    dos = []
    donts = []

    if request.method == 'POST':
        # -------- Read Inputs --------
        data = [
            float(request.form['pm25']),
            float(request.form['pm10']),
            float(request.form['no2']),
            float(request.form['so2']),
            float(request.form['co']),
            float(request.form['o3'])
        ]

        # -------- Predict Using All Algorithms --------
        results = predict_all(data)

        # -------- Select Best Algorithm --------
        best_algo = get_best_algorithm(results, accuracy)
        best_aqi = round(results[best_algo], 2)

        # -------- AQI Interpretation --------
        category = get_aqi_category(best_aqi)
        color = get_aqi_color(best_aqi)
        advice = get_health_advice(best_aqi)
        dos, donts = get_dos_donts(best_aqi)

        # -------- Store Best Result in DB --------
        cursor.execute("""
            INSERT INTO predictions
            (user_id, pm25, pm10, no2, so2, co, o3, algorithm, predicted_aqi)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user'],
            data[0], data[1], data[2],
            data[3], data[4], data[5],
            best_algo,
            best_aqi
        ))
        db.commit()
        session['best_aqi'] = best_aqi
        session['category'] = category
        session['best_algo'] = best_algo
        session['accuracy'] = accuracy
        session['results'] = {k: round(v, 2) for k, v in results.items()}
        session['dos'] = dos
        session['donts'] = donts
        session['advice'] = advice

    # -------- Send Data to UI --------
    return render_template(
        "predict.html",
        results=results,
        accuracy=accuracy,
        best_algo=best_algo,
        best_aqi=best_aqi,
        category=category,
        color=color,
        advice=advice,
        dos=dos,
        donts=donts
    )


def get_pdf_aqi_color(category):
    return {
        "Good": colors.green,
        "Satisfactory": colors.lightblue,
        "Moderate": colors.yellow,
        "Poor": colors.red,
        "Very Poor": colors.purple,
        "Severe": colors.darkred
    }.get(category, colors.grey)

@app.route('/download_pdf')
def download_pdf():
    import io, os
    import matplotlib.pyplot as plt
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    username = session.get('username', 'User')

    # ---------- GET DATA FROM SESSION ----------
    best_algo = session.get('best_algo')
    best_aqi = session.get('best_aqi')
    category = session.get('category')
    advice = session.get('advice')
    dos = session.get('dos', [])
    donts = session.get('donts', [])
    accuracy = session.get('accuracy', {})

    # ---------- COLOR FOR BADGE ----------
    badge_color = {
        "Good": colors.green,
        "Satisfactory": colors.lightblue,
        "Moderate": colors.yellow,
        "Poor": colors.red,
        "Very Poor": colors.purple,
        "Severe": colors.darkred
    }.get(category, colors.grey)

    # ---------- CREATE BAR CHART ----------
    chart_path = "accuracy_chart.png"
    plt.figure()
    plt.bar(accuracy.keys(), accuracy.values())
    plt.ylabel("Accuracy (%)")
    plt.title("Algorithm Accuracy Comparison")
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()

    # ---------- PDF SETUP ----------
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    # ---------- TITLE ----------
    pdf.setFont("Helvetica-Bold", 18)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(width / 2, y, "Air Quality Prediction Report")
    y -= 35

    # ---------- REPORT DATE ----------
    report_datetime = datetime.now().strftime("%d %b %Y | %I:%M %p")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.grey)
    pdf.drawCentredString(width / 2, y, f"Report Generated On : {report_datetime}")
    y -= 30
    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(width / 2, y, f"Generated By : {username}")
    y -= 30

    # ---------- COLORED AQI BADGE ----------
    pdf.setFillColor(badge_color)
    pdf.rect(150, y - 10, 300, 30, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, y, f"AQI {best_aqi}  |  {category}")
    y -= 45

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Best Algorithm : {best_algo}")
    y -= 15

    # ---------- HEALTH ADVICE ----------
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Health Advice")
    y -= 18
    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, y, advice)
    y -= 30

    # ---------- DOs & DONTs ----------
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Do’s")
    pdf.drawString(300, y, "Don’ts")
    y -= 18

    pdf.setFont("Helvetica", 11)
    for i in range(max(len(dos), len(donts))):
        if i < len(dos):
            pdf.drawString(60, y, f"- {dos[i]}")
        if i < len(donts):
            pdf.drawString(310, y, f"- {donts[i]}")
        y -= 14

    y -= 25

    # ---------- AQI SCALE TABLE ----------
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "AQI Category Scale (India – CPCB Standard)")
    y -= 10

    table_data = [
        ["AQI Range", "Category", "Meaning"],
        ["0 – 50", "Good", "Clean air, minimal impact"],
        ["51 – 100", "Satisfactory", "Minor breathing discomfort"],
        ["101 – 200", "Moderate", "Discomfort for heart/lung patients"],
        ["201 – 300", "Poor", "Breathing discomfort for most people"],
        ["301 – 400", "Very Poor", "Respiratory illness on prolonged exposure"],
        ["401 – 500", "Severe", "Serious health effects"]
    ]

    table = Table(table_data, colWidths=[80, 100, 260])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 1, colors.black),

        ("BACKGROUND", (0,1), (-1,1), colors.green),
        ("BACKGROUND", (0,2), (-1,2), colors.lightblue),
        ("BACKGROUND", (0,3), (-1,3), colors.yellow),
        ("BACKGROUND", (0,4), (-1,4), colors.red),
        ("BACKGROUND", (0,5), (-1,5), colors.purple),
        ("BACKGROUND", (0,6), (-1,6), colors.darkred),
        ("TEXTCOLOR", (0,1), (-1,6), colors.white),
    ]))

    table.wrapOn(pdf, width, height)
    table.drawOn(pdf, 50, y - 150)
    y -= 180

    # ---------- ACCURACY CHART ----------
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Algorithm Accuracy Chart")
    y -= 10
    pdf.drawImage(chart_path, 100, y - 160, width=350, height=160)

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    if os.path.exists(chart_path):
        os.remove(chart_path)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Air_Quality_Prediction_Report.pdf"
    )




# ---------- HISTORY ----------
@app.route('/history')
def history():
    cursor.execute(
        "SELECT * FROM predictions WHERE user_id=%s",
        (session['user'],)
    )
    return render_template("history.html", rows=cursor.fetchall())

# ---------- ACCURACY COMPARISON ----------
@app.route('/comparison')
def comparison():
    return render_template("comparison.html", acc=get_accuracy())

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
