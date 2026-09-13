from flask import Flask, render_template, request, redirect, session
import mysql.connector
from mysql.connector import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key')

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='air_ticket_reservation_system'
)

#INDEX 
@app.route('/')
def index():
    session.clear()  
    return render_template('index.html')  


#LOGIN
@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/loginAuth', methods=['POST'])
def loginAuth():
    cursor = conn.cursor(dictionary=True)

    username = request.form['username']
    password = request.form['password']

    #  CUSTOMER 
    cursor.execute("SELECT * FROM customer WHERE email=%s", (username,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password'], password):
        session['user'] = username
        session['role'] = 'customer'
        session['name'] = user['name']
        return redirect('/home')

    #  AGENT 
    cursor.execute("SELECT * FROM booking_agent WHERE email=%s", (username,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password'], password):

        session['user'] = username
        session['role'] = 'agent'
        session['name'] = username

        cursor.execute("""
            SELECT airline_name
            FROM authorized_by
            WHERE booking_agent_email = %s
        """, (username,))

        result = cursor.fetchone()

        if result:
            session['airline'] = result['airline_name']
        else:
            session['airline'] = None

        return redirect('/home')

    #  STAFF 
    cursor.execute("SELECT * FROM airline_staff WHERE username=%s", (username,))
    user = cursor.fetchone()

    if user and check_password_hash(user['password'], password):

        session['user'] = username
        session['role'] = 'staff'
        session['airline'] = user['airline_name']
        session['name'] = user['first_name']

        cursor.execute("""
            SELECT permission FROM staff_permission 
            WHERE staff_username=%s
        """, (username,))

        perms = cursor.fetchall()

        session['permissions'] = [p['permission'] for p in perms] if perms else []

        return redirect('/home')

    return render_template('login.html', error="Invalid username or password")

#  REGISTER 
STAFF_KEY = "STAFF2026"
AGENT_KEY = "AGENT2026"

@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/registerAuth', methods=['POST'])
def registerAuth():
    cursor = conn.cursor()

    username = request.form['username']
    password = generate_password_hash(request.form['password'])
    role = request.form['role']

    try:
        #  CUSTOMER 
        if role == 'customer':
            cursor.execute("""
                INSERT INTO customer 
                (email, name, password, building_number, street, city, state, phone_number, passport_number, passport_expiration_date, passport_country, date_of_birth)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                username,
                request.form['name'],
                password,
                request.form['building_number'],
                request.form['street'],
                request.form['city'],
                request.form['state'],
                request.form['phone_number'],
                request.form['passport_number'],
                request.form['passport_expiration_date'],
                request.form['passport_country'],
                request.form['date_of_birth']
            ))

        #  AGENT 
        elif role == 'agent':
            key = request.form.get('agent_key')

            if key != AGENT_KEY:
                return "Invalid agent authorization key"

            cursor.execute("""
                INSERT INTO booking_agent (email, password)
                VALUES (%s,%s)
            """, (username, password))

        #  STAFF 
        elif role == 'staff':
            key = request.form.get('staff_key')

            if key != STAFF_KEY:
                return "Invalid staff authorization key"

            cursor.execute("""
                INSERT INTO airline_staff 
                (username, password, first_name, last_name, date_of_birth, airline_name)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                username,
                password,
                request.form['first_name'],
                request.form['last_name'],
                request.form['date_of_birth'],
                request.form['airline']
            ))

            # DEFAULT ROLE ASSIGNMENT
            cursor.execute("""
                INSERT INTO staff_permission (staff_username, permission)
                VALUES (%s, %s)
            """, (username, 'operator'))

        else:
            return "Invalid role"

        conn.commit()
        return redirect('/login')
    
    except IntegrityError as e:
        if e.errno == 1062:
            return render_template('register.html', error="Username already exists")
        else:
            return f"Database error: {str(e)}"

    except Exception as e:
        return f"Error registering: {str(e)}"

#  STATUS 
@app.route('/status', methods=['GET','POST'])
def status():
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        airline = request.form.get('airline', '').strip()
        flight_num = request.form.get('flight_num', '').strip()

        cursor.execute("""
            SELECT *,
            CASE
                WHEN NOW() > arrival_time THEN 'completed'
                WHEN NOW() < departure_time THEN 'upcoming'
                WHEN NOW() BETWEEN departure_time AND arrival_time THEN 'in-progress'
                WHEN status = 'delayed' THEN 'delayed'
            END AS real_status
            FROM flight
            WHERE airline_name=%s AND flight_num=%s
        """, (airline, flight_num))

        result = cursor.fetchone()

        if result:
            return render_template('status.html', result=result)
        else:
            return render_template('status.html', error="Flight does not exist")

    return render_template('status.html')

#  HOME 
@app.route('/home', methods=['GET','POST'])
def home():
    print(session)
    if 'user' not in session:
        return redirect('/login')

    cursor = conn.cursor()
    flights = []

    if session.get('role') == 'staff':

        query = """
            SELECT *
            FROM flight
            WHERE airline_name = %s
        """
        params = [session['airline']]

        if request.method == 'POST':
            start = request.form.get('start_date')
            end = request.form.get('end_date')
            dep = request.form.get('departure_airport')
            arr = request.form.get('arrival_airport')

            if start:
                query += " AND DATE(departure_time) >= %s"
                params.append(start)

            if end:
                query += " AND DATE(departure_time) <= %s"
                params.append(end)

            if dep:
                query += " AND departure_airport = %s"
                params.append(dep)

            if arr:
                query += " AND arrival_airport = %s"
                params.append(arr)

        else:
            # DEFAULT: next 30 days
            query += " AND departure_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)"

        query += " ORDER BY departure_time"

        cursor.execute(query, tuple(params))
        flights = cursor.fetchall()

    return render_template('home.html',
                           name=session['name'],
                           role=session['role'],
                           flights=flights)

#Passengers
@app.route('/passengers', methods=['POST'])
def passengers():
    print("FORM:", request.form)
    print("flight_num:", request.form.get("flight_num"))
    print("airline:", request.form.get("airline_name"))

    flight_num = request.form.get('flight_num')
    airline_name = request.form.get('airline_name')

    cursor = conn.cursor()

    query = """
        SELECT p.*
        FROM ticket t
        JOIN purchases p ON t.ticket_id = p.ticket_id
        WHERE t.flight_num = %s
        AND t.airline_name = %s
    """

    cursor.execute(query, (flight_num, airline_name))
    passengers = cursor.fetchall()

    print("DEBUG passengers:", passengers)

    return render_template("passengers.html", passengers=passengers)

#CUSTOMER_FLIGHTS
@app.route('/customer_flights', methods=['GET'])
def customer_flights():
    permissions = session.get('permissions', [])
    if 'admin' not in permissions and 'operator' not in permissions:
        return "Unauthorized"

    cursor = conn.cursor(dictionary=True)


    email = request.args.get('customer_email')
    if not email:
        return "Missing customer email"

    cursor.execute(
        "SELECT name FROM customer WHERE email = %s",
        (email,)
    )
    customer = cursor.fetchone()

    name = customer['name'] if customer else email

    # get flights
    cursor.execute("""
        SELECT f.*
        FROM purchases p
        JOIN ticket t ON p.ticket_id = t.ticket_id
        JOIN flight f 
            ON t.flight_num = f.flight_num 
           AND t.airline_name = f.airline_name
        WHERE p.customer_email = %s
        AND f.airline_name = %s
    """, (email, session['airline']))

    flights = cursor.fetchall()

    return render_template(
        'customer_flights.html',
        flights=flights,
        name=name
    )

#Admin Analytics
@app.route('/admin_analytics')
def admin_analytics():

    permissions = session.get('permissions', [])

    if not any(p in permissions for p in ['admin', 'operator']):
        return redirect('/login')
    cursor = conn.cursor()

    # 1. Top booking agents (tickets)
    cursor.execute("""
        SELECT 
    p.booking_agent_email AS agent,
    COUNT(*) AS tickets_sold
    FROM purchases p
    WHERE p.Booking_agent_email IS NOT NULL
    GROUP BY p.booking_agent_email
    ORDER BY tickets_sold DESC
    """)
    agents_tickets = cursor.fetchall()

    # 2. Top booking agents (commission)
    cursor.execute("""
        SELECT 
    p.booking_agent_email AS agent,
    SUM(f.price) * 0.1 AS commission
    FROM purchases p
    JOIN ticket t ON p.ticket_id = t.ticket_id
    JOIN flight f ON t.flight_num = f.flight_num
    WHERE p.booking_agent_email IS NOT NULL
    GROUP BY p.booking_agent_email
    ORDER BY commission DESC
            """)
    agents_commission = cursor.fetchall()

    # 3. Most frequent customer (last year)
    cursor.execute("""
        SELECT customer_email, COUNT(*) AS cnt
        FROM purchases
        WHERE purchase_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
        GROUP BY customer_email
        ORDER BY cnt DESC
        LIMIT 1
    """)
    top_customer = cursor.fetchall()

    # 4. Tickets sold per month
    cursor.execute("""
        SELECT DATE_FORMAT(purchase_date, '%Y-%m') AS month,
               COUNT(*) AS total
        FROM purchases
        GROUP BY month
        ORDER BY month
    """)
    monthly_tickets = cursor.fetchall()

    # 5. Delay vs On-time
    cursor.execute("""
        SELECT 
            CASE 
                WHEN actual_departure > departure_time THEN 'delayed'
                ELSE 'on-time'
            END AS status,
            COUNT(*) AS cnt,
            ROUND(
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
                2
            ) AS percentage
        FROM flight
        WHERE actual_departure IS NOT NULL
        GROUP BY status
    """)
    delay_stats = cursor.fetchall()

    # 6. Top destinations (3 months)
    cursor.execute("""
    SELECT 
    a.city_name AS destination_city,
    COUNT(*) AS tickets_sold
    FROM purchases p
    JOIN ticket t ON p.ticket_id = t.ticket_id
    JOIN flight f ON t.flight_num = f.flight_num
    JOIN airport a ON f.arrival_airport = a.name
    WHERE f.departure_time >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
    GROUP BY a.city_name
    ORDER BY tickets_sold DESC
    LIMIT 3
    """)
    top_3m = cursor.fetchall()

    # 7. Top destinations (1 year)
    cursor.execute("""
    SELECT 
    a.city_name AS destination_city,
    COUNT(*) AS tickets_sold
    FROM purchases p
    JOIN ticket t ON p.ticket_id = t.ticket_id
    JOIN flight f ON t.flight_num = f.flight_num
    JOIN airport a ON f.arrival_airport = a.name
    WHERE f.departure_time >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
    GROUP BY a.city_name
    ORDER BY tickets_sold DESC
    LIMIT 3
    """)
    top_1y = cursor.fetchall()
    print("agents_tickets:", agents_tickets)
    print("agents_commission:", agents_commission)
    print("top_customer:", top_customer)
    print("monthly_tickets:", monthly_tickets)
    print("delay_stats:", delay_stats)
    print("top_3m:", top_3m)
    print("top_1y:", top_1y)

    return render_template(
        "admin_analytics.html",
        agents_tickets=agents_tickets,
        agents_commission=agents_commission,
        top_customer=top_customer,
        monthly_tickets=monthly_tickets,
        delay_stats=delay_stats,
        top_3m=top_3m,
        top_1y=top_1y
    )

#  SEARCH 
@app.route('/search', methods=['GET', 'POST'])
def search():
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        dep = request.form.get('departure_airport', '').strip()
        arr = request.form.get('arrival_airport', '').strip()
        date = request.form.get('date', '').strip()

        query = """
        SELECT f.*,
        CASE
            WHEN f.status = 'delayed' THEN 'delayed'
            WHEN NOW() < f.departure_time THEN 'upcoming'
            WHEN NOW() BETWEEN f.departure_time AND f.arrival_time THEN 'in-progress'
            ELSE 'completed'
        END AS real_status
        FROM flight f
        WHERE f.status = 'upcoming'
        """

        params = []

        # FROM
        if dep:
            query += """
            AND (
                f.departure_airport = %s
                OR f.departure_airport IN (
                    SELECT name FROM airport
                    WHERE city_name = %s
                    OR city_name IN (
                        SELECT city_name FROM city_alias WHERE alias_name = %s
                    )
                )
            )
            """
            params += [dep, dep, dep]

        # TO 
        if arr:
            query += """
            AND (
                f.arrival_airport = %s
                OR f.arrival_airport IN (
                    SELECT name FROM airport
                    WHERE city_name = %s
                    OR city_name IN (
                        SELECT city_name FROM city_alias WHERE alias_name = %s
                    )
                )
            )
            """
            params += [arr, arr, arr]

        # DATE filter
        if date:
            query += " AND DATE(f.departure_time) = %s"
            params.append(date)

        cursor.execute(query, tuple(params))
        flights = cursor.fetchall()

        if flights:
            return render_template('search.html', flights=flights)
        else:
            return render_template('search.html', flights=[], error="No flights found")

    return render_template('search.html')


#  BOOK 
@app.route('/book', methods=['POST'])
def book():
    if 'user' not in session:
        return redirect('/login')

    cursor = conn.cursor()
    flight_num = request.form['flight_num']
    airline = request.form['airline_name']

    try:
        # ================= VALIDATION =================

        # 1. DOUBLE BOOKING CHECK
        if session['role'] == 'customer':
            cursor.execute("""
                SELECT *
                FROM purchases p
                JOIN ticket t ON p.ticket_id = t.ticket_id
                WHERE p.customer_email = %s
                AND t.flight_num = %s
                AND t.airline_name = %s
            """, (session['user'], flight_num, airline))

            if cursor.fetchone():
                return "You already booked this flight"

        elif session['role'] == 'agent':
            customer_email = request.form['customer_email']

            cursor.execute("""
                SELECT *
                FROM purchases p
                JOIN ticket t ON p.ticket_id = t.ticket_id
                WHERE p.customer_email = %s
                AND t.flight_num = %s
                AND t.airline_name = %s
            """, (customer_email, flight_num, airline))

            if cursor.fetchone():
                return "This customer already booked this flight"

            #this was not checked before the ticket creation before thats why it got error
            cursor.execute("""
                SELECT *
                FROM authorized_by
                WHERE booking_agent_email = %s
                AND airline_name = %s
            """, (session['user'], airline))

            if not cursor.fetchone():
                return "Not authorized"

        # 2. CAPACITY CHECK
        cursor.execute("""
            SELECT seat_capacity
            FROM airplane a
            JOIN flight f 
                ON a.id = f.airplane_id 
               AND a.airline_name = f.airline_name
            WHERE f.flight_num = %s 
              AND f.airline_name = %s
        """, (flight_num, airline))

        capacity = cursor.fetchone()
        if not capacity:
            return "Flight not found"

        capacity = capacity[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ticket
            WHERE flight_num = %s AND airline_name = %s
        """, (flight_num, airline))

        sold = cursor.fetchone()[0]

        if sold >= capacity:
            return "Flight Full"



        # 3. CREATE TICKET
        cursor.execute("SELECT MAX(ticket_id) FROM ticket")
        tid = (cursor.fetchone()[0] or 0) + 1

        cursor.execute("""
            INSERT INTO ticket VALUES (%s, %s, %s)
        """, (tid, airline, flight_num))

        # 4. PURCHASE
        if session['role'] == 'customer':
            cursor.execute("""
                INSERT INTO purchases VALUES (%s, NULL, %s, CURDATE())
            """, (session['user'], tid))

        elif session['role'] == 'agent':
            cursor.execute("""
                INSERT INTO purchases VALUES (%s, %s, %s, CURDATE())
            """, (customer_email, session['user'], tid))

        conn.commit()
        return render_template("booking_success.html")

    except Exception as e:
        conn.rollback()
        return f"Error occurred: {str(e)}"


#  MY FLIGHTS 
@app.route('/myflights', methods=['GET','POST'])
def myflights():
    if session.get('role') != 'customer':
        return redirect('/home')

    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT f.*,
        CASE
            WHEN f.status = 'delayed' THEN 'delayed'
            WHEN NOW() < f.departure_time THEN 'upcoming'
            WHEN NOW() BETWEEN f.departure_time AND f.arrival_time THEN 'in-progress'
            ELSE 'past'
        END AS real_status
        FROM purchases p
        JOIN ticket t ON p.ticket_id=t.ticket_id
        JOIN flight f ON t.flight_num=f.flight_num AND t.airline_name=f.airline_name
        WHERE p.customer_email=%s
    """
    params = [session['user']]

    if request.method == 'POST':
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        origin = request.form.get('origin', '').strip()
        destination = request.form.get('destination', '').strip()

        if start_date:
            query += " AND DATE(f.departure_time) >= %s"
            params.append(start_date)

        if end_date:
            query += " AND DATE(f.departure_time) <= %s"
            params.append(end_date)

        if origin:
            query += " AND f.departure_airport = %s"
            params.append(origin)

        if destination:
            query += " AND f.arrival_airport = %s"
            params.append(destination)

    else:
        # DEFAULT: upcoming flights only
        query += " AND f.departure_time >= NOW()"

    query += " ORDER BY f.departure_time ASC"

    cursor.execute(query, tuple(params))
    flights = cursor.fetchall()

    return render_template('myflights.html', flights=flights)


#SPENDING
@app.route('/spending', methods=['GET','POST'])
def spending():
    if session.get('role') != 'customer':
        return redirect('/home')

    cursor = conn.cursor()
    user = session['user']

    if request.method == 'POST':
        start = request.form.get('start_date')
        end = request.form.get('end_date')

        # TOTAL
        cursor.execute("""
            SELECT SUM(f.price)
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            JOIN flight f ON t.flight_num = f.flight_num AND t.airline_name = f.airline_name
            WHERE p.customer_email = %s
            AND DATE(p.purchase_date) BETWEEN %s AND %s
        """, (user, start, end))
        total = cursor.fetchone()[0] or 0

        # MONTHLY (CUSTOM RANGE)
        cursor.execute("""
            SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month, SUM(f.price)
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            JOIN flight f ON t.flight_num = f.flight_num AND t.airline_name = f.airline_name
            WHERE p.customer_email = %s
            AND DATE(p.purchase_date) BETWEEN %s AND %s
            GROUP BY month
            ORDER BY month
        """, (user, start, end))
        data = cursor.fetchall()

        months = [row[0] for row in data]
        amounts = [float(row[1]) for row in data]

    else:
        # TOTAL (12 months)
        cursor.execute("""
            SELECT SUM(f.price)
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            JOIN flight f ON t.flight_num = f.flight_num AND t.airline_name = f.airline_name
            WHERE p.customer_email = %s
            AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        """, (user,))
        total = cursor.fetchone()[0] or 0

        # MONTHLY (last 6 months)
        cursor.execute("""
            SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month, SUM(f.price)
            FROM purchases p
            JOIN ticket t ON p.ticket_id = t.ticket_id
            JOIN flight f ON t.flight_num = f.flight_num AND t.airline_name = f.airline_name
            WHERE p.customer_email = %s
            AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY month
            ORDER BY month
        """, (user,))
        data = cursor.fetchall()
        print(data)

        from datetime import datetime
        from dateutil.relativedelta import relativedelta

        months_full = []
        today = datetime.today()

        for i in range(5, -1, -1):
            m = (today - relativedelta(months=i)).strftime('%Y-%m')
            months_full.append(m)

        data_dict = {row[0]: float(row[1]) for row in data}

        months = months_full
        amounts = [data_dict.get(m, 0) for m in months_full]

    return render_template('spending.html',
                           total=total,
                           months=months,
                           amounts=amounts)
# AGENGT ANALYTICS
@app.route('/agent_analytics')
def agent_analytics():
    if session.get('role') != 'agent':
        return redirect('/login')

    cursor = conn.cursor()
    agent_email = session['user']

    # 1. Total commission (last 30 days)
    cursor.execute("""
        SELECT COALESCE(ROUND(SUM(f.price) * 0.1, 2), 0) AS total_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_id = t.ticket_id
        JOIN flight f ON t.flight_num = f.flight_num
        WHERE p.booking_agent_email = %s
        AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """, (agent_email,))
    total_commission = cursor.fetchone()[0]

    # 2. Average commission per ticket
    cursor.execute("""
        SELECT COALESCE(ROUND(AVG(f.price * 0.1), 2), 0) AS avg_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_id = t.ticket_id
        JOIN flight f ON t.flight_num = f.flight_num
        WHERE p.booking_agent_email = %s
        AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """, (agent_email,))
    avg_commission = cursor.fetchone()[0]

    # 3. Tickets sold
    cursor.execute("""
        SELECT COUNT(*)
        FROM purchases
        WHERE booking_agent_email = %s
        AND purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """, (agent_email,))
    tickets_sold = cursor.fetchone()[0]

    # 4. Top 5 customers (tickets, last 6 months)
    cursor.execute("""
        SELECT customer_email, COUNT(*) AS tickets
        FROM purchases
        WHERE booking_agent_email = %s
        AND purchase_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY customer_email
        ORDER BY tickets DESC
        LIMIT 5
    """, (agent_email,))
    top_customers_tickets = cursor.fetchall()

    # 5. Top 5 customers (commission, last year)
    cursor.execute("""
        SELECT p.customer_email, SUM(f.price * 0.1) AS commission
        FROM purchases p
        JOIN ticket t ON p.ticket_id = t.ticket_id
        JOIN flight f ON t.flight_num = f.flight_num
        WHERE p.booking_agent_email = %s
        AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email
        ORDER BY commission DESC
        LIMIT 5
    """, (agent_email,))
    top_customers_commission = cursor.fetchall()

    return render_template(
        'agent_analytics.html',
        total_commission=total_commission,
        avg_commission=avg_commission,
        tickets_sold=tickets_sold,
        top_customers_tickets=top_customers_tickets,
        top_customers_commission=top_customers_commission
    )


#Staff 
@app.route('/staff')
def staff_panel():
    if 'user' not in session or session.get('role') != 'staff':
        return redirect('/login')

    return render_template('staff.html')

#ADMIN 
@app.route('/add_airport', methods=['POST'])
def add_airport():
    if 'admin' not in session.get('permissions', []):
        return "Unauthorized", 403

    cursor = conn.cursor()

    airport_name = request.form['name']
    city_name = request.form['city']

    cursor.execute("""
        INSERT INTO airport (name, city_name)
        VALUES (%s, %s)
    """, (airport_name, city_name))

    conn.commit()
    return "Airport added"

@app.route('/add_plane', methods=['POST'])
def add_plane():
    if 'admin' not in session.get('permissions', []):
        return "Unauthorized", 403

    cursor = conn.cursor(dictionary=True)

  
    cursor.execute("""
        SELECT airline_name
        FROM airline_staff
        WHERE username = %s
    """, (session['user'],))

    staff = cursor.fetchone()

    if not staff:
        return "Staff not found", 404

    airline = staff['airline_name']

    plane_id = request.form.get('id')
    capacity = request.form.get('capacity')

    if not plane_id or not capacity:
        return "Missing required fields", 400

    # NUMERIC VALIDATION
    try:
        capacity = int(capacity)
        if capacity <= 0:
            return "Capacity must be greater than 0", 400
    except:
        return "Invalid capacity", 400

    # airline check
    if request.form.get('airline_name') and request.form['airline_name'] != airline:
        return "You cannot create airplanes for another airline", 403

    # duplicate check
    cursor.execute("""
        SELECT *
        FROM airplane
        WHERE id = %s AND airline_name = %s
    """, (plane_id, airline))

    if cursor.fetchone():
        return "Airplane already exists for this airline", 400

    cursor.execute("""
        INSERT INTO airplane (id, airline_name, seat_capacity)
        VALUES (%s, %s, %s)
    """, (
        plane_id,
        airline,
        capacity
    ))

    conn.commit()
    return "Plane added successfully"

from datetime import datetime

@app.route('/create_flight', methods=['POST'])
def create_flight():
    if 'admin' not in session.get('permissions', []):
        return "Unauthorized", 403

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT airline_name
        FROM airline_staff
        WHERE username = %s
    """, (session['user'],))

    staff = cursor.fetchone()

    if not staff:
        return "Staff not found", 404

    airline = staff['airline_name']

  
    required = [
        'flight_num', 'departure_time', 'arrival_time',
        'price', 'status', 'departure_airport',
        'arrival_airport', 'airplane_id'
    ]

    for field in required:
        if not request.form.get(field):
            return f"{field} is required", 400

    # PRICE VALIDATION
    try:
        price = float(request.form['price'])
        if price <= 0:
            return "Price must be greater than 0", 400
    except:
        return "Invalid price", 400

    # DATE VALIDATION
    try:
        departure = datetime.strptime(request.form['departure_time'], "%Y-%m-%d %H:%M:%S")
        arrival = datetime.strptime(request.form['arrival_time'], "%Y-%m-%d %H:%M:%S")

        if departure >= arrival:
            return "Departure must be before arrival", 400
    except:
        return "Invalid date format", 400

    # airline enforcement
    if request.form.get('airline_name') and request.form['airline_name'] != airline:
        return "You are not allowed to create flights for other airlines", 403

    cursor.execute("""
        INSERT INTO flight (
            flight_num,
            airline_name,
            departure_time,
            arrival_time,
            price,
            status,
            departure_airport,
            arrival_airport,
            airplane_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        request.form['flight_num'],
        airline,
        request.form['departure_time'],
        request.form['arrival_time'],
        price,
        request.form['status'],
        request.form['departure_airport'],
        request.form['arrival_airport'],
        request.form['airplane_id']
    ))

    conn.commit()
    return "Flight created"

@app.route('/assign_permission', methods=['POST'])
def assign_permission():
    if 'admin' not in session.get('permissions', []):
        return "Unauthorized"

    cursor = conn.cursor()
    cursor.execute("""
        REPLACE INTO staff_permission VALUES (%s,%s)
    """, (request.form['staff_username'], request.form['permission']))
    conn.commit()
    return "Permission assigned"

@app.route('/authorize_agent', methods=['POST'])
def authorize_agent():
    if 'admin' not in session.get('permissions', []):
        return "Unauthorized", 403

    cursor = conn.cursor()

    agent_email = request.form['agent_email']
    airline = request.form['airline_name']

    try:
        # check if already authorized
        cursor.execute("""
            SELECT * FROM authorized_by 
            WHERE booking_agent_email=%s AND airline_name=%s
        """, (agent_email, airline))

        if cursor.fetchone():
            return "Agent already authorized for this airline"

        # Insert authorization
        cursor.execute("""
            INSERT INTO authorized_by (booking_agent_email, airline_name)
            VALUES (%s, %s)
        """, (agent_email, airline))

        conn.commit()
        return "Agent successfully authorized"

    except Exception as e:
        return f"Error: {str(e)}"
    
@app.route('/agent_flights', methods=['GET','POST'])
def agent_flights():
    if session.get('role') != 'agent':
        return redirect('/login')

    cursor = conn.cursor(dictionary=True)
    agent = session['user']

    query = """
    SELECT 
        f.flight_num, f.airline_name, f.departure_time, f.arrival_time,
        f.price, f.status, f.departure_airport, f.arrival_airport,
        c.name AS customer_name
    FROM purchases p
    JOIN ticket t ON p.ticket_id = t.ticket_id
    JOIN flight f ON t.flight_num = f.flight_num AND t.airline_name = f.airline_name
    JOIN customer c ON p.customer_email = c.email
    WHERE p.booking_agent_email = %s
"""
    params = [agent]

    if request.method == 'POST':
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        dep = request.form.get('departure_airport')
        arr = request.form.get('arrival_airport')

        if start:
            query += " AND DATE(f.departure_time) >= %s"
            params.append(start)

        if end:
            query += " AND DATE(f.departure_time) <= %s"
            params.append(end)

        if dep:
            query += " AND f.departure_airport = %s"
            params.append(dep)

        if arr:
            query += " AND f.arrival_airport = %s"
            params.append(arr)

    query += " ORDER BY f.departure_time DESC"

    cursor.execute(query, tuple(params))
    flights = cursor.fetchall()

    return render_template('agent_flights.html', flights=flights)

# Operator, admin
@app.route('/update_status', methods=['POST'])
def update_status():
    permissions = session.get('permissions', [])

    if 'operator' not in permissions and 'admin' not in permissions:
        return "Unauthorized", 403

    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE flight 
            SET status=%s
            WHERE flight_num=%s AND airline_name=%s
        """, (
            request.form['status'],
            request.form['flight'],
            session['airline']
        ))

        if cursor.rowcount == 0:
            return "No matching flight found or not allowed"

        conn.commit()
        return "Updated successfully"

    except Exception as e:
        return f"Error: {str(e)}"


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    print("AFTER LOGOUT:", session)
    return redirect('/')

app.run(debug=True)
