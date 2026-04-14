from flask import Flask, render_template, request, redirect, url_for, session, flash
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
        db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        username TEXT UNIQUE NOT NULL, 
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL, 
                        is_premium INTEGER DEFAULT 0)''')
        
        db.execute('''CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, 
                        category TEXT NOT NULL, price TEXT NOT NULL, contact TEXT NOT NULL, 
                        image_url TEXT, user_id INTEGER, 
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        db.execute('''CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, 
                        keyword TEXT, 
                        category TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
                        
        db.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, 
                        item_id INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(item_id) REFERENCES items(id),
                        UNIQUE(user_id, item_id))''')
        db.commit()

# --- ROUTES ---

@app.route('/')
@app.route('/')
def index():
    db = get_db()
    search_query = request.args.get('q', '').strip()
    category = request.args.get('cat', '').strip()
    sort = request.args.get('sort', '').strip()
    
    # Khởi tạo câu truy vấn cơ bản
    query = "SELECT * FROM items WHERE 1=1"
    params = []

    # Thêm điều kiện tìm kiếm từ khóa
    if search_query:
        query += " AND (title LIKE ? OR category LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    
    # Thêm điều kiện lọc theo danh mục
    if category:
        query += " AND category = ?"
        params.append(category)

    # Thêm logic sắp xếp
    if sort == 'price_asc':
        query += " ORDER BY CAST(price AS INTEGER) ASC"
    elif sort == 'price_desc':
        query += " ORDER BY CAST(price AS INTEGER) DESC"
    else:
        query += " ORDER BY id DESC"
    
    items = db.execute(query, params).fetchall()
    
    # Logic thông báo wishlist giữ nguyên...
    notifications = []
    if 'user_id' in session:
        user_alerts = db.execute('SELECT * FROM alerts WHERE user_id = ?', (session['user_id'],)).fetchall()
        for alert in user_alerts:
            match = db.execute('''SELECT title FROM items WHERE title LIKE ? LIMIT 1''', 
                               (f"%{alert['keyword']}%",)).fetchone()
            if match:
                notifications.append(f"Khớp từ khóa '{alert['keyword']}': {match['title']}")
        
    return render_template('index.html', 
                           items=items, 
                           search_query=search_query, 
                           current_cat=category, 
                           current_sort=sort,
                           notifications=notifications)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'].lower().strip()
        password = request.form['password']
        
        if not email.endswith('@hcmut.edu.vn'):
            flash('Registration failed: You must use an @hcmut.edu.vn email address.')
            return render_template('register.html')

        db = get_db()
        try:
            db.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, password))
            db.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already exists.')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_premium'] = user['is_premium']
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        flash('Please login to sell items.')
        return redirect(url_for('login'))

    db = get_db()
    if session.get('is_premium') == 0:
        item_count = db.execute('SELECT COUNT(*) FROM items WHERE user_id = ?', (session['user_id'],)).fetchone()[0]
        if item_count >= 2:
            flash('Free tier limit reached (Max 2 items). Please upgrade to Premium!')
            return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        price = request.form['price']
        image_url = request.form['image_url']
        contact = request.form['contact']
        db.execute('INSERT INTO items (title, category, price, image_url, contact, user_id) VALUES (?, ?, ?, ?, ?, ?)', 
                   (title, category, price, image_url, contact, session['user_id']))
        db.commit()
        flash('Item listed successfully!')
        return redirect(url_for('index'))
    return render_template('add_item.html')

# --- WISHLIST & KEYWORD ALERTS ROUTES ---

@app.route('/wishlist')
def view_wishlist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    query = '''
        SELECT i.* FROM items i 
        JOIN wishlist w ON i.id = w.item_id 
        WHERE w.user_id = ? 
        ORDER BY w.id DESC
    '''
    items = db.execute(query, (session['user_id'],)).fetchall()
    alerts = db.execute('SELECT * FROM alerts WHERE user_id = ?', (session['user_id'],)).fetchall()
    
    notifications = []
    for alert in alerts:
        match = db.execute('''SELECT title FROM items WHERE title LIKE ? LIMIT 1''', 
                           (f"%{alert['keyword']}%",)).fetchone()
        if match:
            notifications.append(f"Matching '{alert['keyword']}': {match['title']}")
            
    return render_template('wishlist.html', items=items, alerts=alerts, notifications=notifications)

@app.route('/wishlist/add/<int:item_id>', methods=['POST'])
def add_to_wishlist(item_id):
    if 'user_id' not in session:
        flash('Please login to use the wishlist.')
        return redirect(url_for('login'))
        
    db = get_db()
    
    if session.get('is_premium') == 0:
        count = db.execute('SELECT COUNT(*) FROM wishlist WHERE user_id = ?', (session['user_id'],)).fetchone()[0]
        if count >= 5:
            flash('Free tier limit reached (Max 5 wishlist items). Upgrade to Premium to save more!')
            return redirect(request.referrer or url_for('index'))
            
    try:
        db.execute('INSERT INTO wishlist (user_id, item_id) VALUES (?, ?)', (session['user_id'], item_id))
        db.commit()
        flash('Item added to wishlist!')
    except sqlite3.IntegrityError:
        flash('Item is already in your wishlist.')
        
    return redirect(request.referrer or url_for('index'))

@app.route('/wishlist/remove/<int:item_id>', methods=['POST'])
def remove_from_wishlist(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    db.execute('DELETE FROM wishlist WHERE user_id = ? AND item_id = ?', (session['user_id'], item_id))
    db.commit()
    flash('Item removed from wishlist.')
    
    return redirect(request.referrer or url_for('view_wishlist'))

@app.route('/add_alert', methods=['POST'])
def add_alert():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    keyword = request.form.get('keyword').strip()
    db = get_db()
    
    if session.get('is_premium') == 0:
        count = db.execute('SELECT COUNT(*) FROM alerts WHERE user_id = ?', (session['user_id'],)).fetchone()[0]
        if count >= 1:
            flash('Free tier limit reached (Max 1 tracked keyword). Please upgrade to Premium!')
            return redirect(request.referrer or url_for('index'))
            
    db.execute('INSERT INTO alerts (user_id, keyword) VALUES (?, ?)', (session['user_id'], keyword))
    db.commit()
    flash(f'Now tracking keyword: "{keyword}"')
    
    return redirect(request.referrer or url_for('view_wishlist'))

@app.route('/remove_alert/<int:alert_id>', methods=['POST'])
def remove_alert(alert_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    db.execute('DELETE FROM alerts WHERE id = ? AND user_id = ?', (alert_id, session['user_id']))
    db.commit()
    flash('Tracked keyword removed.')
    return redirect(request.referrer or url_for('view_wishlist'))

@app.route('/upgrade')
def upgrade():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE users SET is_premium = 1 WHERE id = ?', (session['user_id'],))
    db.commit()
    session['is_premium'] = 1
    flash('You are now a Premium user.')
    return redirect(url_for('index'))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ? AND user_id = ?', (item_id, session['user_id']))
    db.execute('DELETE FROM wishlist WHERE item_id = ?', (item_id,))
    db.commit()
    flash('Item removed.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    else:
        db = get_db()
        try:
            db.execute('SELECT email FROM users LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('ALTER TABLE users ADD COLUMN email TEXT UNIQUE')
            db.commit()
            
        try:
            db.execute('SELECT * FROM wishlist LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            user_id INTEGER, 
                            item_id INTEGER,
                            FOREIGN KEY(user_id) REFERENCES users(id),
                            FOREIGN KEY(item_id) REFERENCES items(id),
                            UNIQUE(user_id, item_id))''')
            db.commit()
            
    app.run(debug=True)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    db = get_db()
    # Lấy thông tin sản phẩm và tên người bán
    item = db.execute('''
        SELECT i.*, u.username 
        FROM items i 
        JOIN users u ON i.user_id = u.id 
        WHERE i.id = ?
    ''', (item_id,)).fetchone()
    
    if not item:
        flash("Không tìm thấy sản phẩm.")
        return redirect(url_for('index'))
        
    return render_template('item_detail.html', item=item)