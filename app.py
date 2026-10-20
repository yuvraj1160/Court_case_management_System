from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_pbl'

def get_db_connection():
    return psycopg2.connect(
        host="localhost", database="court_case_db", user="postgres",
        password="1234", port="5432"  # Make sure this matches your real PostgreSQL password (set to '1234' from previous config)
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM Users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['username'] = username
            session['role'] = user[0]
            return redirect(url_for('index'))
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    role = session['role']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cases, hearings, audit_logs = [], [], []
    
    if role in ['admin', 'clerk']:
        cursor.execute("SELECT case_number, status, filing_date FROM Cases ORDER BY filing_date DESC LIMIT 7;")
        cases = cursor.fetchall()
        
    if role in ['admin', 'judge']:
        limit = 5 if role == 'judge' else 10
        cursor.execute(f"SELECT j.name, c.case_number, h.start_time::time, h.start_time::date FROM Hearings h JOIN Judges j ON h.judge_id = j.judge_id JOIN Cases c ON h.case_id = c.case_id WHERE h.start_time > CURRENT_DATE ORDER BY h.start_time ASC LIMIT {limit};")
        hearings = cursor.fetchall()
        
    if role == 'admin':
        cursor.execute("SELECT log_id, action_type, changed_at::time FROM Audit_Logs ORDER BY changed_at DESC LIMIT 5;")
        audit_logs = cursor.fetchall()
        
    cursor.close()
    conn.close()
    
    return render_template('index.html', role=role, username=session['username'], cases=cases, hearings=hearings, audit_logs=audit_logs)

@app.route('/add_case', methods=['POST'])
def add_case():
    if session.get('role') != 'clerk':
        return redirect(url_for('index'))
    
    case_number = request.form['case_number']
    status = request.form['status']
    filing_date = request.form['filing_date']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Cases (case_number, status, filing_date) VALUES (%s, %s, %s)", (case_number, status, filing_date))
        cursor.execute("INSERT INTO Audit_Logs (action_type) VALUES (%s)", (f"Added New Case: {case_number}",))
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/update_status', methods=['POST'])
def update_status():
    if session.get('role') != 'clerk':
        return redirect(url_for('index'))
        
    case_number = request.form['case_number_update']
    new_status = request.form['new_status']
    reason = request.form['update_reason']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Cases SET status = %s WHERE case_number = %s", (new_status, case_number))
        cursor.execute("INSERT INTO Audit_Logs (action_type) VALUES (%s)", (f"Updated Case {case_number} to {new_status}. Reason: {reason}",))
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
