from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import date
import random

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------------- DATABASE ---------------- #

def get_db():
    return sqlite3.connect("dermascan.db")

def init_db():
    with get_db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS skin_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_date TEXT,
            image_path TEXT,
            risk_score REAL,
            risk_level TEXT,
            skin_condition TEXT,
            symptoms TEXT
        )
        """)
        
        # Add columns if they don't exist
        cursor = con.cursor()
        cursor.execute("PRAGMA table_info(skin_records)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'skin_condition' not in columns:
            con.execute("ALTER TABLE skin_records ADD COLUMN skin_condition TEXT")
        if 'symptoms' not in columns:
            con.execute("ALTER TABLE skin_records ADD COLUMN symptoms TEXT")
        
        con.commit()

init_db()

# ---------------- MOCK ML MODEL ---------------- #
# (replace this later with your real model)

def predict_risk(image_path):
    risk_score = round(random.uniform(0.3, 0.9), 2)

    if risk_score < 0.5:
        level = "Low"
    elif risk_score < 0.7:
        level = "Medium"
    else:
        level = "High"

    return risk_score, level

# ---------------- COMPARISON LOGIC ---------------- #

def get_all_records():
    """Retrieve all records ordered by date"""
    with get_db() as con:
        cursor = con.cursor()
        cursor.execute("""
            SELECT id, upload_date, image_path, risk_score, risk_level, skin_condition, symptoms
            FROM skin_records
            ORDER BY upload_date ASC
        """)
        return cursor.fetchall()

def get_latest_record():
    """Get the most recent record"""
    with get_db() as con:
        cursor = con.cursor()
        cursor.execute("""
            SELECT id, upload_date, image_path, risk_score, risk_level, skin_condition, symptoms
            FROM skin_records
            ORDER BY upload_date DESC
            LIMIT 1
        """)
        return cursor.fetchone()

def get_previous_record(current_date):
    """Get the previous record before current date"""
    with get_db() as con:
        cursor = con.cursor()
        cursor.execute("""
            SELECT id, upload_date, image_path, risk_score, risk_level, skin_condition, symptoms
            FROM skin_records
            WHERE upload_date < ?
            ORDER BY upload_date DESC
            LIMIT 1
        """, (current_date,))
        return cursor.fetchone()

def analyze_changes(current_record, previous_record):
    """Compare current and previous records to detect changes"""
    if not previous_record:
        return {
            'is_first_upload': True,
            'changes': [],
            'internal_signs': [],
            'risk_change': None,
            'improvement_percentage': None,
            'days_elapsed': None
        }
    
    curr_score = current_record[3]  # risk_score
    prev_score = previous_record[3]
    
    from datetime import datetime
    curr_date = datetime.strptime(current_record[1], '%Y-%m-%d')
    prev_date = datetime.strptime(previous_record[1], '%Y-%m-%d')
    days_diff = (curr_date - prev_date).days
    
    risk_change = curr_score - prev_score
    improvement_percentage = ((prev_score - curr_score) / prev_score * 100) if prev_score > 0 else 0
    
    changes = []
    internal_signs = []
    
    # Risk trend analysis
    if risk_change < -0.15:
        changes.append("✅ Significant improvement detected")
    elif risk_change < -0.05:
        changes.append("🟢 Slight improvement detected")
    elif risk_change > 0.15:
        changes.append("🔴 Significant deterioration detected")
    elif risk_change > 0.05:
        changes.append("🟡 Mild deterioration detected")
    else:
        changes.append("➡️ Condition remains stable")
    
    # Risk level changes
    if current_record[4] != previous_record[4]:
        changes.append(f"Risk level changed: {previous_record[4]} → {current_record[4]}")
    
    # Symptom analysis
    curr_symptoms = current_record[6] or ""
    prev_symptoms = previous_record[6] or ""
    
    if curr_symptoms and prev_symptoms:
        curr_symp_list = set(curr_symptoms.split(','))
        prev_symp_list = set(prev_symptoms.split(','))
        
        new_symptoms = curr_symp_list - prev_symp_list
        resolved_symptoms = prev_symp_list - curr_symp_list
        
        if new_symptoms:
            internal_signs.append(f"🔴 New symptoms: {', '.join(new_symptoms)}")
        if resolved_symptoms:
            internal_signs.append(f"✅ Resolved symptoms: {', '.join(resolved_symptoms)}")
        if not new_symptoms and not resolved_symptoms:
            internal_signs.append("➡️ Symptoms unchanged")
    
    # Condition analysis
    curr_condition = current_record[5] or "Normal"
    prev_condition = previous_record[5] or "Normal"
    
    if curr_condition != prev_condition:
        internal_signs.append(f"Skin condition changed: {prev_condition} → {curr_condition}")
    
    return {
        'is_first_upload': False,
        'changes': changes,
        'internal_signs': internal_signs,
        'risk_change': round(risk_change, 3),
        'improvement_percentage': round(improvement_percentage, 1),
        'days_elapsed': days_diff,
        'previous_date': previous_record[1],
        'previous_score': prev_score
    }

def compare_with_previous(today, current_risk):
    with get_db() as con:
        cursor = con.cursor()
        cursor.execute("""
            SELECT risk_score, upload_date
            FROM skin_records
            ORDER BY id DESC
            LIMIT 1 OFFSET 1
        """)
        row = cursor.fetchone()

    if not row:
        return "🟢 First upload. No comparison available."

    prev_risk, prev_date = row
    diff = current_risk - prev_risk

    if diff > 0.15:
        return f"🔴 Risk increased significantly (+{round(diff*100)}%). Please consult a dermatologist."
    elif diff > 0.05:
        return "🟡 Mild risk progression detected."
    else:
        return "🟢 No significant change detected."

# ---------------- ROUTES ---------------- #

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if 'image' not in request.files:
            if request.headers.get('Content-Type') == 'application/json' or request.accept_mimetypes.get('application/json'):
                return jsonify({'error': 'No image file provided'}), 400
            return render_template("upload.html", message="❌ No image selected"), 400

        image = request.files['image']
        skin_condition = request.form.get('skin_condition', 'Normal')
        symptoms = request.form.get('symptoms', '')
        
        if image.filename == '':
            if request.headers.get('Content-Type') == 'application/json' or request.accept_mimetypes.get('application/json'):
                return jsonify({'error': 'No image selected'}), 400
            return render_template("upload.html", message="❌ No image selected"), 400

        try:
            filename = f"{date.today()}_{image.filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(path)

            risk_score, risk_level = predict_risk(path)

            # Get the previous record BEFORE inserting new record
            all_before = get_all_records()
            previous_record = all_before[-1] if all_before else None

            with get_db() as con:
                con.execute("""
                    INSERT INTO skin_records (upload_date, image_path, risk_score, risk_level, skin_condition, symptoms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (str(date.today()), path, risk_score, risk_level, skin_condition, symptoms))

            # Get the current record we just inserted
            current_record = get_latest_record()
            
            # Analyze changes
            analysis = analyze_changes(current_record, previous_record)
            
            # Get all records for graph
            all_records = get_all_records()
            graph_data = {
                'dates': [rec[1] for rec in all_records],
                'scores': [rec[3] for rec in all_records]
            }

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.get('application/json'):
                return jsonify({
                    'success': True,
                    'risk_score': risk_score,
                    'risk_level': risk_level,
                    'skin_condition': skin_condition,
                    'symptoms': symptoms,
                    'analysis': analysis,
                    'graph_data': graph_data,
                    'upload_date': str(date.today())
                }), 200

            return render_template("upload.html", 
                message="✅ Image analyzed successfully",
                risk_score=risk_score,
                risk_level=risk_level
            ), 200

        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.get('application/json'):
                return jsonify({'error': error_msg}), 500
            return render_template("upload.html", message=f"❌ {error_msg}"), 500

    # GET request - show upload page with historical data
    try:
        all_records = get_all_records()
        graph_data = {
            'dates': [rec[1] for rec in all_records],
            'scores': [rec[3] for rec in all_records],
            'levels': [rec[4] for rec in all_records]
        }
        return render_template("upload.html", graph_data=graph_data, all_records=all_records)
    except:
        return render_template("upload.html")

@app.route("/chatbot")
def chatbot():
    """Serve chatbot.html"""
    try:
        with open('chatbot.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading chatbot: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
