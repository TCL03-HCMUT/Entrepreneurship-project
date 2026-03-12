from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'hcmut_super_secret_key'
DATABASE = 'hcmut_market.db'

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        # CHANGED: Replaced 'username' with 'email'
        db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        email TEXT UNIQUE NOT NULL, 
                        password TEXT NOT NULL)''')
                        
        # CHANGED: Added 'is_promoted' column to items
        db.execute('''CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        title TEXT NOT NULL, 
                        category TEXT NOT NULL, 
                        price TEXT NOT NULL, 
                        contact TEXT NOT NULL, 
                        image_url TEXT, 
                        is_promoted INTEGER DEFAULT 0,
                        user_id INTEGER, 
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
        db.commit()

# --- HTML TEMPLATES ---
BASE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HCMUT Trade</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .hcmut-bg { background-color: #003399; }
        .hcmut-text { color: #003399; }
        .item-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .item-card:hover { transform: translateY(-5px); box-shadow: 0 .5rem 1rem rgba(0,0,0,.15)!important; }
        .card-img-top { height: 200px; object-fit: cover; }
        .no-img-placeholder { height: 200px; background-color: #e9ecef; color: #6c757d; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        /* NEW: Styling for Promoted Items */
        .promoted-card { border: 2px solid #ffc107 !important; box-shadow: 0 0 10px rgba(255, 193, 7, 0.3); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark hcmut-bg shadow-sm mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Bách Khoa Exchange</a>
            <div class="d-flex align-items-center">
                <a class="nav-link text-white me-3" href="/">Market</a>
                {% if session.user_id %}
                    <a class="btn btn-light btn-sm fw-bold me-3 text-primary" href="/add">+ Sell Item</a>
                    <a class="nav-link text-white opacity-75" href="/logout">Logout ({{ session.email.split('@')[0] }})</a>
                {% else %}
                    <a class="nav-link text-white me-3" href="/login">Login</a>
                    <a class="btn btn-outline-light btn-sm fw-bold" href="/register">Student Register</a>
                {% endif %}
            </div>
        </div>
    </nav>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category if category != 'message' else 'warning' }} shadow-sm alert-dismissible fade show" role="alert">
                    {{ message }}
                </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

MARKET_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="hcmut-text fw-bold m-0">Available Materials & Books</h2>
    </div>

    <div class="card shadow-sm border-0 mb-4 p-3 bg-white">
        <form method="GET" action="/" class="d-flex">
            <input type="text" name="q" class="form-control bg-light me-2" placeholder="Search for 'Giải Tích', 'Kit vi điều khiển', etc..." value="{{ search_query }}">
            <button type="submit" class="btn hcmut-bg text-white fw-bold px-4">Search</button>
            {% if search_query %}
                <a href="/" class="btn btn-outline-secondary ms-2 fw-bold">Clear</a>
            {% endif %}
        </form>
    </div>

    <div class="row">
        {% for item in items %}
            <div class="col-md-4 mb-4">
                <div class="card h-100 shadow-sm border-0 item-card {% if item.is_promoted %}promoted-card{% endif %}">
                    {% if item.image_url %}
                        <img src="{{ item.image_url }}" class="card-img-top rounded-top" alt="{{ item.title }}">
                    {% else %}
                        <div class="no-img-placeholder rounded-top">No Image Provided</div>
                    {% endif %}
                    
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-primary">{{ item.category }}</span>
                            {% if item.is_promoted %}
                                <span class="badge bg-warning text-dark fw-bold shadow-sm">🔥 HOT ITEM</span>
                            {% endif %}
                        </div>
                        
                        <h5 class="card-title hcmut-text fw-bold">{{ item.title }}</h5>
                        <h6 class="card-subtitle mb-3 text-danger fw-bold">{{ item.price }} VND</h6>
                        <p class="card-text mb-1"><strong>Contact:</strong></p>
                        <span class="badge bg-secondary fs-6">{{ item.contact }}</span>
                    </div>
                    
                    <div class="card-footer bg-white border-top-0 text-muted d-flex justify-content-between align-items-center mb-2">
                        <small>Seller ID: {{ item.user_id }}</small>
                        
                        {% if session.user_id == item.user_id %}
                            <div class="d-flex gap-2">
                                {% if not item.is_promoted %}
                                <form action="/promote/{{ item.id }}" method="POST" class="m-0">
                                    <button type="submit" class="btn btn-sm btn-warning fw-bold">🚀 Promote</button>
                                </form>
                                {% endif %}
                                <form action="/delete/{{ item.id }}" method="POST" class="m-0">
                                    <button type="submit" class="btn btn-sm btn-outline-danger">Mark Sold</button>
                                </form>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        {% else %}
            <div class="col-12">
                <div class="alert alert-info bg-white border-0 shadow-sm text-center py-4">
                    {% if search_query %}
                        <strong>No results found.</strong> Try a different keyword!
                    {% else %}
                        No items listed yet.
                    {% endif %}
                </div>
            </div>
        {% endfor %}
    </div>
''')

ADD_ITEM_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <div class="row justify-content-center">
        <div class="col-md-6 mt-4 mb-5">
            <div class="card shadow-sm border-0 p-4">
                <h3 class="hcmut-text mb-4 fw-bold">List a New Item (Free!)</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label fw-bold">Item Name</label>
                        <input type="text" class="form-control bg-light" name="title" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold">Category</label>
                        <select class="form-select bg-light" name="category" required>
                            <option value="Sách Đại Cương">Sách Đại Cương (General Books)</option>
                            <option value="Sách Chuyên Ngành">Sách Chuyên Ngành (Major Books)</option>
                            <option value="Linh Kiện Điện Tử">Linh Kiện Điện Tử (Electronics)</option>
                            <option value="Dụng Cụ Học Tập">Dụng Cụ Học Tập (Study Tools)</option>
                            <option value="Khác">Khác (Other)</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold">Price (VND)</label>
                        <input type="number" class="form-control bg-light" name="price" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold">Image URL (Optional)</label>
                        <input type="url" class="form-control bg-light" name="image_url">
                    </div>
                    <div class="mb-4">
                        <label class="form-label fw-bold">Contact Info</label>
                        <input type="text" class="form-control bg-light" name="contact" required>
                    </div>
                    <button type="submit" class="btn hcmut-bg text-white w-100 fw-bold py-2">Post Listing</button>
                </form>
            </div>
        </div>
    </div>
''')

AUTH_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <div class="row justify-content-center">
        <div class="col-md-5 mt-5">
            <div class="card shadow border-0 p-4">
                <h3 class="hcmut-text text-center mb-4 fw-bold">{{ action }}</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label fw-bold">Student Email</label>
                        <input type="email" class="form-control bg-light" name="email" placeholder="sv@hcmut.edu.vn" required>
                        {% if action == 'Register' %}
                            <div class="form-text text-success fw-bold">Must end with @hcmut.edu.vn</div>
                        {% endif %}
                    </div>
                    <div class="mb-4">
                        <label class="form-label fw-bold">Password</label>
                        <input type="password" class="form-control bg-light" name="password" required>
                    </div>
                    <button type="submit" class="btn hcmut-bg text-white w-100 fw-bold py-2">{{ action }}</button>
                </form>
            </div>
        </div>
    </div>
''')

# --- ROUTES ---

@app.route('/')
def index():
    db = get_db()
    search_query = request.args.get('q', '').strip()
    
    # NEW: Items are now ordered by is_promoted DESC first, then by ID. 
    # This guarantees paid/bumped items sit at the very top of the page.
    if search_query:
        wildcard_query = f"%{search_query}%"
        items = db.execute('''
            SELECT * FROM items 
            WHERE title LIKE ? OR category LIKE ? 
            ORDER BY is_promoted DESC, id DESC
        ''', (wildcard_query, wildcard_query)).fetchall()
    else:
        items = db.execute('SELECT * FROM items ORDER BY is_promoted DESC, id DESC').fetchall()
        
    return render_template_string(MARKET_HTML, items=items, search_query=search_query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        # NEW: Absolute Trust Validation! Block non-HCMUT emails.
        if not email.endswith('@hcmut.edu.vn'):
            flash('Registration denied. You must use a valid @hcmut.edu.vn student email address.', 'danger')
            return redirect(url_for('register'))

        db = get_db()
        try:
            db.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            db.commit()
            flash('Registration successful! Welcome to the marketplace.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('This email is already registered.', 'danger')
    return render_template_string(AUTH_HTML, action="Register")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['email'] = user['email']
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template_string(AUTH_HTML, action="Login")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        flash('Please login to sell items.', 'warning')
        return redirect(url_for('login'))

    # NEW: The 2-item freemium limit is completely gone! Users can list endlessly to build your supply.

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        contact = request.form['contact']
        
        db = get_db()
        db.execute('INSERT INTO items (title, category, price, image_url, contact, user_id) VALUES (?, ?, ?, ?, ?, ?)', 
                   (title, category, price, image_url, contact, session['user_id']))
        db.commit()
        flash('Item listed successfully! It is live on the market.', 'success')
        return redirect(url_for('index'))
        
    return render_template_string(ADD_ITEM_HTML)

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ? AND user_id = ?', (item_id, session['user_id']))
    db.commit()
    flash('Item marked as sold!', 'success')
    return redirect(url_for('index'))

# NEW: Route to handle the "Promote" micro-transaction
@app.route('/promote/<int:item_id>', methods=['POST'])
def promote_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    # In a real app, this is where you would redirect them to MoMo or VNPay API.
    # For the MVP, we assume they paid the 10,000 VND and update the database immediately.
    
    db.execute('UPDATE items SET is_promoted = 1 WHERE id = ? AND user_id = ?', (item_id, session['user_id']))
    db.commit()
    
    flash('Payment successful! Your item is now Promoted to the top of the page.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)