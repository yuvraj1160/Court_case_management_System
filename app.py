from flask import Flask, render_template
import psycopg2

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="court_case_db",
        user="postgres",
        password="1234",
        port="5432"
    )

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT case_number, status, filing_date FROM Cases ORDER BY filing_date DESC LIMIT 7;")
    cases = cursor.fetchall()
    
    cursor.execute("""
        SELECT j.name, c.case_number, h.start_time::time 
        FROM Hearings h
        JOIN Judges j ON h.judge_id = j.judge_id
        JOIN Cases c ON h.case_id = c.case_id
        WHERE h.start_time > CURRENT_DATE
        ORDER BY h.start_time ASC LIMIT 5;
    """)
    hearings = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', cases=cases, hearings=hearings)

if __name__ == '__main__':
    app.run(debug=True)
