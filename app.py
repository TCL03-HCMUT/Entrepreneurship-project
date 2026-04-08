from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from database import get_db, check_migrations

app = Flask(__name__)
app.secret_key = 'hcmut_super_secret_key'

@app.route('/')
def index():
    db = get_db()
    search_query = request.args.get('q', '').strip()
    
    if search_query:
        wildcard_query = f"%{search_query}%"
        items = db.execute('''SELECT * FROM items WHERE title LIKE ? OR category LIKE ? ORDER BY id DESC''', 
                           (wildcard_query, wildcard_query)).fetchall()
    else:
        items = db.execute('SELECT * FROM items ORDER BY id DESC').fetchall()
    
    notifications = []
    if 'user_id' in session:
        user_alerts = db.execute('SELECT * FROM alerts WHERE user_id = ?', (session['user_id'],)).fetchall()
        for alert in user_alerts:
            match = db.execute('''SELECT title FROM items WHERE title LIKE ? LIMIT 1''', 
                               (f"%{alert['keyword']}%",)).fetchone()
            if match:
                notifications.append(f"Matching '{alert['keyword']}': {match['title']}")
        
    return render_template('market.html', items=items, search_query=search_query, notifications=notifications)

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

@app.route('/wishlist')
def view_wishlist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    query = '''SELECT i.* FROM items i JOIN wishlist w ON i.id = w.item_id WHERE w.user_id = ? ORDER BY w.id DESC'''
    items = db.execute(query, (session['user_id'],)).fetchall()
    alerts = db.execute('SELECT * FROM alerts WHERE user_id = ?', (session['user_id'],)).fetchall()
    
    notifications = []
    for alert in alerts:
        match = db.execute('''SELECT title FROM items WHERE title LIKE ? LIMIT 1''', (f"%{alert['keyword']}%",)).fetchone()
        if match: notifications.append(f"Matching '{alert['keyword']}': {match['title']}")
            
    return render_template('wishlist.html', items=items, alerts=alerts, notifications=notifications)

@app.route('/wishlist/add/<int:item_id>', methods=['POST'])
def add_to_wishlist(item_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db()
    if session.get('is_premium') == 0:
        if db.execute('SELECT COUNT(*) FROM wishlist WHERE user_id = ?', (session['user_id'],)).fetchone()[0] >= 5:
            flash('Free tier limit reached (Max 5 wishlist items).')
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
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM wishlist WHERE user_id = ? AND item_id = ?', (session['user_id'], item_id))
    db.commit()
    flash('Item removed from wishlist.')
    return redirect(request.referrer or url_for('view_wishlist'))

@app.route('/add_alert', methods=['POST'])
def add_alert():
    if 'user_id' not in session: return redirect(url_for('login'))
    keyword = request.form.get('keyword').strip()
    db = get_db()
    if session.get('is_premium') == 0:
        if db.execute('SELECT COUNT(*) FROM alerts WHERE user_id = ?', (session['user_id'],)).fetchone()[0] >= 1:
            flash('Free tier limit reached (Max 1 tracked keyword).')
            return redirect(request.referrer or url_for('index'))
    db.execute('INSERT INTO alerts (user_id, keyword) VALUES (?, ?)', (session['user_id'], keyword))
    db.commit()
    flash(f'Now tracking keyword: "{keyword}"')
    return redirect(request.referrer or url_for('view_wishlist'))

@app.route('/remove_alert/<int:alert_id>', methods=['POST'])
def remove_alert(alert_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM alerts WHERE id = ? AND user_id = ?', (alert_id, session['user_id']))
    db.commit()
    flash('Tracked keyword removed.')
    return redirect(request.referrer or url_for('view_wishlist'))

@app.route('/upgrade')
def upgrade():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE users SET is_premium = 1 WHERE id = ?', (session['user_id'],))
    db.commit()
    session['is_premium'] = 1
    flash('You are now a Premium user.')
    return redirect(url_for('index'))

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ? AND user_id = ?', (item_id, session['user_id']))
    db.execute('DELETE FROM wishlist WHERE item_id = ?', (item_id,))
    db.commit()
    flash('Item removed.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        check_migrations()
    app.run(debug=True)