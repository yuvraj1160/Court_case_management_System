import psycopg2
from faker import Faker
import random
from datetime import timedelta

# Faker initialize karein (Indian names aur data generate karne ke liye)
fake = Faker('en_IN')

# ---------------------------------------------------------
# DATABASE CONNECTION (Yahan apna password dalein)
# ---------------------------------------------------------
DB_HOST = "localhost"
DB_NAME = "court_case_db"
DB_USER = "postgres"
DB_PASS = "1234" # <-- Apna pgAdmin wala password yahan daalein
DB_PORT = "5432"

try:
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
    cursor = conn.cursor()
    print("Database connected successfully!")
except Exception as e:
    print(f"Error connecting to database: {e}")
    exit()

# ---------------------------------------------------------
# DATA GENERATION VARIABLES
# ---------------------------------------------------------
NUM_JUDGES = 20
NUM_PARTIES = 500
NUM_CASES = 1000  # Ye 1000 cases generate karega (Total rows 10,000+ cross ho jayengi)

# Memory lists (taaki aage foreign keys link kar sakein)
judge_ids = []
party_ids = []
case_ids = []
hearing_ids = []

print("Generating Data. This might take a minute or two...")

# 1. GENERATE JUDGES
print("Inserting Judges...")
for _ in range(NUM_JUDGES):
    name = f"Hon'ble Justice {fake.name()}"
    status = random.choice([True, True, True, False]) # Mostly true
    cursor.execute("INSERT INTO Judges (name, active_status) VALUES (%s, %s) RETURNING judge_id", (name, status))
    judge_ids.append(cursor.fetchone()[0])
conn.commit()

# 2. GENERATE PARTIES (and Phone Numbers)
print("Inserting Parties...")
party_types = ['Petitioner', 'Respondent', 'Lawyer']
for _ in range(NUM_PARTIES):
    name = fake.name()
    p_type = random.choice(party_types)
    cursor.execute("INSERT INTO Parties (name, party_type) VALUES (%s, %s) RETURNING party_id", (name, p_type))
    p_id = cursor.fetchone()[0]
    party_ids.append(p_id)
    
    # Generate 1 or 2 phone numbers per party
    for _ in range(random.randint(1, 2)):
        # Ensure exact 10 digits for phone number to avoid VARCHAR limit errors if any
        phone = fake.numerify(text='##########') 
        cursor.execute("INSERT INTO Party_Phones (party_id, phone_number) VALUES (%s, %s) ON CONFLICT DO NOTHING", (p_id, phone))
conn.commit()

# 3. GENERATE CASES
print("Inserting Cases...")
statuses = ['Filed', 'Active', 'Adjourned', 'Disposed', 'Closed']
while len(case_ids) < NUM_CASES:
    case_no = f"CC-{fake.year()}-{random.randint(100000, 9999999)}"
    status = random.choice(statuses)
    filing_date = fake.date_between(start_date='-5y', end_date='today')
    try:
        cursor.execute("INSERT INTO Cases (case_number, status, filing_date) VALUES (%s, %s, %s) RETURNING case_id", (case_no, status, filing_date))
        case_ids.append(cursor.fetchone()[0])
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        continue
conn.commit()

# 4. GENERATE PARTY_CASE_ROLES (Bridge Table)
print("Mapping Parties to Cases...")
for case_id in case_ids:
    # Randomly assign 2 to 4 parties per case
    assigned_parties = random.sample(party_ids, k=random.randint(2, 4))
    for p_id in assigned_parties:
        role = random.choice(['Lead Counsel', 'Applicant', 'Defendant'])
        cursor.execute("INSERT INTO Party_Case_Roles (party_id, case_id, role_type) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (p_id, case_id, role))
conn.commit()

# 5. GENERATE HEARINGS (With safe times to avoid conflicts)
print("Scheduling Hearings...")
for case_id in case_ids:
    # Not all cases have hearings yet
    if random.choice([True, False]): 
        j_id = random.choice(judge_ids)
        # To avoid the strictly enforced overlap constraint, we pick a very random specific time
        h_start = fake.date_time_between(start_date='-1y', end_date='+1y')
        # Hearing lasts 1 hour
        h_end = h_start + timedelta(hours=1) 
        
        try:
            cursor.execute("INSERT INTO Hearings (case_id, judge_id, start_time, end_time) VALUES (%s, %s, %s, %s) RETURNING hearing_id", (case_id, j_id, h_start, h_end))
            hearing_ids.append(cursor.fetchone()[0])
        except (psycopg2.errors.ExclusionViolation, Exception):
            # Our database constraint worked! The judge was double booked, so it blocked it.
            conn.rollback() # Reset transaction and skip this one
            continue
conn.commit()

# 6. GENERATE ORDERS & DISPOSITIONS
print("Generating Orders and Dispositions...")
for case_id in case_ids:
    # Add an order
    if random.choice([True, False]):
        j_id = random.choice(judge_ids)
        order_date = fake.date_between(start_date='-1y', end_date='today')
        details = fake.sentence(nb_words=10)
        cursor.execute("INSERT INTO Orders (case_id, judge_id, order_date, details) VALUES (%s, %s, %s, %s)", (case_id, j_id, order_date, details))
    
    # Add a disposition if the case status requires it
    cursor.execute("SELECT status FROM Cases WHERE case_id = %s", (case_id,))
    status = cursor.fetchone()[0]
    if status in ['Disposed', 'Closed']:
        judgement = fake.paragraph(nb_sentences=3)
        disp_date = fake.date_between(start_date='-1m', end_date='today')
        cursor.execute("INSERT INTO Dispositions (case_id, final_judgment, disposition_date) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (case_id, judgement, disp_date))
conn.commit()

# Close connection
cursor.close()
conn.close()
print("[SUCCESS] Database is now populated with thousands of records!")