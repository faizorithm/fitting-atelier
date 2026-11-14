from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

DB = 'fitting_atelier.db'

# ── DB helpers ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_username VARCHAR NOT NULL,
            user_email VARCHAR NOT NULL UNIQUE,
            user_password_hash VARCHAR NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Brand (
            brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name VARCHAR NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Category (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name VARCHAR NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ClothingItem (
            clothing_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            clothing_item_name VARCHAR NOT NULL,
            clothing_item_color VARCHAR,
            clothing_item_size VARCHAR,
            clothing_item_price FLOAT,
            FOREIGN KEY (user_id) REFERENCES User(user_id),
            FOREIGN KEY (brand_id) REFERENCES Brand(brand_id),
            FOREIGN KEY (category_id) REFERENCES Category(category_id)
        );
        CREATE TABLE IF NOT EXISTS Outfit (
            outfit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            outfit_name VARCHAR NOT NULL,
            outfit_occasion VARCHAR,
            outfit_hijab_color VARCHAR,
            FOREIGN KEY (user_id) REFERENCES User(user_id)
        );
        CREATE TABLE IF NOT EXISTS OutfitItem (
            outfit_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            outfit_id INTEGER NOT NULL,
            clothing_item_id INTEGER NOT NULL,
            FOREIGN KEY (outfit_id) REFERENCES Outfit(outfit_id),
            FOREIGN KEY (clothing_item_id) REFERENCES ClothingItem(clothing_item_id)
        );

        INSERT OR IGNORE INTO Brand (brand_name) VALUES
            ('Nike'),('Adidas'),('Zara'),('H&M'),('Uniqlo'),('Other');
        INSERT OR IGNORE INTO Category (category_name) VALUES
            ('Tops'),('Bottoms'),('Shoes'),('Outerwear'),('Accessories'),('Dress');
    ''')
    conn.commit()
    conn.close()

# ── WTForms ─────────────────────────────────────────────────
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Register')

class LoginForm(FlaskForm):
    email    = StringField('Email',    validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Log In')

class ClothingItemForm(FlaskForm):
    name     = StringField('Item Name', validators=[DataRequired()])
    color    = StringField('Color')
    size     = SelectField('Size', choices=[('XS','XS'),('S','S'),('M','M'),('L','L'),('XL','XL'),('One Size','One Size')])
    price    = FloatField('Price ($)', validators=[DataRequired()])
    brand_id = SelectField('Brand', coerce=int, validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    submit   = SubmitField('Add Item')

class OutfitForm(FlaskForm):
    name         = StringField('Outfit Name', validators=[DataRequired()])
    occasion     = SelectField('Occasion', choices=[('Casual','Casual'),('Formal','Formal'),('Athletic','Athletic'),('Everyday','Everyday')])
    hijab_color  = StringField('Hijab Color')
    submit       = SubmitField('Save Outfit')

# ── Routes ───────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        conn = get_db()
        existing = conn.execute('SELECT * FROM User WHERE user_email=?', (form.email.data,)).fetchone()
        if existing:
            flash('Email already registered.', 'error')
            conn.close()
            return redirect(url_for('register'))
        conn.execute('INSERT INTO User (user_username, user_email, user_password_hash) VALUES (?,?,?)',
            (form.username.data, form.email.data, generate_password_hash(form.password.data)))
        conn.commit()
        conn.close()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db()
        user = conn.execute('SELECT * FROM User WHERE user_email=?', (form.email.data,)).fetchone()
        conn.close()
        if user and check_password_hash(user['user_password_hash'], form.password.data):
            session['user_id']   = user['user_id']
            session['username']  = user['user_username']
            return redirect(url_for('wardrobe'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/wardrobe')
def wardrobe():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    items = conn.execute('''
        SELECT ci.*, b.brand_name, cat.category_name
        FROM ClothingItem ci
        JOIN Brand b ON ci.brand_id = b.brand_id
        JOIN Category cat ON ci.category_id = cat.category_id
        WHERE ci.user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('wardrobe.html', items=items)

@app.route('/add_item', methods=['GET','POST'])
def add_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    form = ClothingItemForm()
    form.brand_id.choices    = [(b['brand_id'], b['brand_name']) for b in conn.execute('SELECT * FROM Brand').fetchall()]
    form.category_id.choices = [(c['category_id'], c['category_name']) for c in conn.execute('SELECT * FROM Category').fetchall()]
    if form.validate_on_submit():
        conn.execute('''INSERT INTO ClothingItem
            (user_id, brand_id, category_id, clothing_item_name, clothing_item_color, clothing_item_size, clothing_item_price)
            VALUES (?,?,?,?,?,?,?)''',
            (session['user_id'], form.brand_id.data, form.category_id.data,
             form.name.data, form.color.data, form.size.data, form.price.data))
        conn.commit()
        conn.close()
        flash('Item added!', 'success')
        return redirect(url_for('wardrobe'))
    conn.close()
    return render_template('add_item.html', form=form)

@app.route('/outfits')
def outfits():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    outfits = conn.execute('SELECT * FROM Outfit WHERE user_id=?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('outfits.html', outfits=outfits)

@app.route('/add_outfit', methods=['GET','POST'])
def add_outfit():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    form = OutfitForm()
    items = conn.execute('''
        SELECT ci.*, b.brand_name FROM ClothingItem ci
        JOIN Brand b ON ci.brand_id = b.brand_id
        WHERE ci.user_id=?
    ''', (session['user_id'],)).fetchall()
    if request.method == 'POST' and form.validate_on_submit():
        cur = conn.execute('''INSERT INTO Outfit (user_id, outfit_name, outfit_occasion, outfit_hijab_color)
            VALUES (?,?,?,?)''',
            (session['user_id'], form.name.data, form.occasion.data, form.hijab_color.data))
        outfit_id = cur.lastrowid
        selected = request.form.getlist('item_ids')
        for item_id in selected:
            conn.execute('INSERT INTO OutfitItem (outfit_id, clothing_item_id) VALUES (?,?)', (outfit_id, item_id))
        conn.commit()
        conn.close()
        flash('Outfit saved!', 'success')
        return redirect(url_for('outfits'))
    conn.close()
    return render_template('add_outfit.html', form=form, items=items)

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM ClothingItem WHERE clothing_item_id=? AND user_id=?', (item_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('wardrobe'))

@app.route('/delete_outfit/<int:outfit_id>')
def delete_outfit(outfit_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM OutfitItem WHERE outfit_id=?', (outfit_id,))
    conn.execute('DELETE FROM Outfit WHERE outfit_id=? AND user_id=?', (outfit_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('outfits'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
