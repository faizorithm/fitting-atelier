
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, FloatField, SelectField,
    PasswordField, SubmitField
)
from wtforms.validators import DataRequired, Email, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from ai.recommender import recommend_clothing, recommend_outfit

import sqlite3
import os


# ==========================================
# FLASK CONFIGURATION
# ==========================================

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing. Set it before running Flask."
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "fitting_atelier.db")


# ==========================================
# DATABASE
# ==========================================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS User (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_username TEXT NOT NULL,
                user_email TEXT NOT NULL UNIQUE,
                user_password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS Brand (
                brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS Category (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ClothingItem (
                clothing_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                brand_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                clothing_item_name TEXT NOT NULL,
                clothing_item_color TEXT,
                clothing_item_size TEXT,
                clothing_item_price REAL,
                FOREIGN KEY (user_id) REFERENCES User(user_id),
                FOREIGN KEY (brand_id) REFERENCES Brand(brand_id),
                FOREIGN KEY (category_id) REFERENCES Category(category_id)
            );

            CREATE TABLE IF NOT EXISTS Outfit (
                outfit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                outfit_name TEXT NOT NULL,
                outfit_occasion TEXT,
                outfit_hijab_color TEXT,
                FOREIGN KEY (user_id) REFERENCES User(user_id)
            );

            CREATE TABLE IF NOT EXISTS OutfitItem (
                outfit_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                outfit_id INTEGER NOT NULL,
                clothing_item_id INTEGER NOT NULL,
                FOREIGN KEY (outfit_id) REFERENCES Outfit(outfit_id),
                FOREIGN KEY (clothing_item_id) REFERENCES ClothingItem(clothing_item_id)
            );
        """)

        brands = [
            "Nike", "Adidas", "Zara",
            "H&M", "Uniqlo", "Other"
        ]

        for brand in brands:
            conn.execute("""
                INSERT INTO Brand (brand_name)
                SELECT ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM Brand WHERE brand_name = ?
                )
            """, (brand, brand))

        categories = [
            "Tops", "Bottoms", "Shoes",
            "Outerwear", "Accessories", "Dress"
        ]

        for category in categories:
            conn.execute("""
                INSERT INTO Category (category_name)
                SELECT ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM Category WHERE category_name = ?
                )
            """, (category, category))

        conn.commit()

    finally:
        conn.close()


# ==========================================
# FORMS
# ==========================================

class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired()]
    )

    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired()]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    submit = SubmitField("Log In")


class ClothingItemForm(FlaskForm):
    name = StringField(
        "Item Name",
        validators=[DataRequired()]
    )

    color = StringField("Color")

    size = SelectField(
        "Size",
        choices=[
            ("XS", "XS"),
            ("S", "S"),
            ("M", "M"),
            ("L", "L"),
            ("XL", "XL"),
            ("One Size", "One Size")
        ]
    )

    price = FloatField(
        "Price ($)",
        validators=[
            DataRequired(),
            NumberRange(min=0)
        ]
    )

    brand_id = SelectField(
        "Brand",
        coerce=int,
        validators=[DataRequired()]
    )

    category_id = SelectField(
        "Category",
        coerce=int,
        validators=[DataRequired()]
    )

    submit = SubmitField("Add Item")


class OutfitForm(FlaskForm):
    name = StringField(
        "Outfit Name",
        validators=[DataRequired()]
    )

    occasion = SelectField(
        "Occasion",
        choices=[
            ("Casual", "Casual"),
            ("Formal", "Formal"),
            ("Athletic", "Athletic"),
            ("Everyday", "Everyday")
        ]
    )

    hijab_color = StringField("Hijab Color")

    submit = SubmitField("Save Outfit")


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():
    return render_template("home.html")


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        conn = get_db()

        try:
            existing = conn.execute("""
                SELECT user_id
                FROM User
                WHERE user_email = ?
            """, (form.email.data,)).fetchone()

            if existing:
                flash("Email already registered.", "error")
                return redirect(url_for("register"))

            conn.execute("""
                INSERT INTO User (
                    user_username,
                    user_email,
                    user_password_hash
                )
                VALUES (?, ?, ?)
            """, (
                form.username.data,
                form.email.data,
                generate_password_hash(form.password.data)
            ))

            conn.commit()

        finally:
            conn.close()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        conn = get_db()

        try:
            user = conn.execute("""
                SELECT *
                FROM User
                WHERE user_email = ?
            """, (form.email.data,)).fetchone()

        finally:
            conn.close()

        if user and check_password_hash(
            user["user_password_hash"],
            form.password.data
        ):
            session.clear()
            session["user_id"] = user["user_id"]
            session["username"] = user["user_username"]

            flash("Welcome back!", "success")
            return redirect(url_for("wardrobe"))

        flash("Invalid email or password.", "error")

    return render_template("login.html", form=form)


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ==========================================
# WARDROBE
# ==========================================

@app.route("/wardrobe")
def wardrobe():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    try:
        items = conn.execute("""
            SELECT
                ci.*,
                b.brand_name,
                cat.category_name
            FROM ClothingItem ci
            JOIN Brand b
                ON ci.brand_id = b.brand_id
            JOIN Category cat
                ON ci.category_id = cat.category_id
            WHERE ci.user_id = ?
            ORDER BY ci.clothing_item_id DESC
        """, (session["user_id"],)).fetchall()

    finally:
        conn.close()

    return render_template("wardrobe.html", items=items)


# ==========================================
# ADD ITEM
# ==========================================

@app.route("/add_item", methods=["GET", "POST"])
def add_item():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    form = ClothingItemForm()

    try:
        brands = conn.execute("""
            SELECT
                MIN(brand_id) AS brand_id,
                brand_name
            FROM Brand
            GROUP BY brand_name
            ORDER BY brand_name
        """).fetchall()

        categories = conn.execute("""
            SELECT
                MIN(category_id) AS category_id,
                category_name
            FROM Category
            GROUP BY category_name
            ORDER BY category_name
        """).fetchall()

        form.brand_id.choices = [
            (b["brand_id"], b["brand_name"])
            for b in brands
        ]

        form.category_id.choices = [
            (c["category_id"], c["category_name"])
            for c in categories
        ]

        if form.validate_on_submit():
            conn.execute("""
                INSERT INTO ClothingItem (
                    user_id,
                    brand_id,
                    category_id,
                    clothing_item_name,
                    clothing_item_color,
                    clothing_item_size,
                    clothing_item_price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session["user_id"],
                form.brand_id.data,
                form.category_id.data,
                form.name.data,
                form.color.data,
                form.size.data,
                form.price.data
            ))

            conn.commit()

            flash("Item added!", "success")
            return redirect(url_for("wardrobe"))

    finally:
        conn.close()

    return render_template("add_item.html", form=form)


# ==========================================
# DELETE ITEM
# ==========================================

@app.route("/delete_item/<int:item_id>")
def delete_item(item_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    try:
        conn.execute("""
            DELETE FROM OutfitItem
            WHERE clothing_item_id IN (
                SELECT clothing_item_id
                FROM ClothingItem
                WHERE clothing_item_id = ?
                AND user_id = ?
            )
        """, (item_id, session["user_id"]))

        conn.execute("""
            DELETE FROM ClothingItem
            WHERE clothing_item_id = ?
            AND user_id = ?
        """, (item_id, session["user_id"]))

        conn.commit()

    finally:
        conn.close()

    return redirect(url_for("wardrobe"))


# ==========================================
# OUTFITS
# ==========================================

@app.route("/outfits")
def outfits():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    try:
        outfits = conn.execute("""
            SELECT *
            FROM Outfit
            WHERE user_id = ?
        """, (session["user_id"],)).fetchall()

    finally:
        conn.close()

    return render_template("outfits.html", outfits=outfits)


# ==========================================
# ADD OUTFIT
# ==========================================

@app.route("/add_outfit", methods=["GET", "POST"])
def add_outfit():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    form = OutfitForm()

    try:
        items = conn.execute("""
            SELECT ci.*, b.brand_name
            FROM ClothingItem ci
            JOIN Brand b
                ON ci.brand_id = b.brand_id
            WHERE ci.user_id = ?
        """, (session["user_id"],)).fetchall()

        if form.validate_on_submit():
            selected = request.form.getlist("item_ids")

            allowed_ids = {
                str(item["clothing_item_id"])
                for item in items
            }

            if any(
                item_id not in allowed_ids
                for item_id in selected
            ):
                flash("Invalid wardrobe item selected.", "error")
                return redirect(url_for("add_outfit"))

            cursor = conn.execute("""
                INSERT INTO Outfit (
                    user_id,
                    outfit_name,
                    outfit_occasion,
                    outfit_hijab_color
                )
                VALUES (?, ?, ?, ?)
            """, (
                session["user_id"],
                form.name.data,
                form.occasion.data,
                form.hijab_color.data
            ))

            outfit_id = cursor.lastrowid

            for item_id in set(selected):
                conn.execute("""
                    INSERT INTO OutfitItem (
                        outfit_id,
                        clothing_item_id
                    )
                    VALUES (?, ?)
                """, (outfit_id, item_id))

            conn.commit()

            flash("Outfit saved!", "success")
            return redirect(url_for("outfits"))

    finally:
        conn.close()

    return render_template(
        "add_outfit.html",
        form=form,
        items=items
    )


# ==========================================
# DELETE OUTFIT
# ==========================================

@app.route("/delete_outfit/<int:outfit_id>")
def delete_outfit(outfit_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    try:
        conn.execute("""
            DELETE FROM OutfitItem
            WHERE outfit_id IN (
                SELECT outfit_id
                FROM Outfit
                WHERE outfit_id = ?
                AND user_id = ?
            )
        """, (outfit_id, session["user_id"]))

        conn.execute("""
            DELETE FROM Outfit
            WHERE outfit_id = ?
            AND user_id = ?
        """, (outfit_id, session["user_id"]))

        conn.commit()

    finally:
        conn.close()

    return redirect(url_for("outfits"))


# ==========================================
# AI OUTFIT RECOMMENDATIONS
# ==========================================

@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    if "user_id" not in session:
        return redirect(url_for("login"))

    outfit_result = None
    user_request = ""

    conn = get_db()

    try:
        clothing_items = conn.execute("""
            SELECT
                ci.*,
                b.brand_name,
                cat.category_name
            FROM ClothingItem ci
            JOIN Brand b
                ON ci.brand_id = b.brand_id
            JOIN Category cat
                ON ci.category_id = cat.category_id
            WHERE ci.user_id = ?
            ORDER BY ci.clothing_item_id DESC
        """, (session["user_id"],)).fetchall()

    finally:
        conn.close()

    wardrobe_count = len(clothing_items)

    if request.method == "POST":
        user_request = request.form.get(
            "user_request", ""
        ).strip()

        if user_request and clothing_items:
            outfit_result = recommend_outfit(
                user_request,
                clothing_items
            )

    return render_template(
        "recommendations.html",
        outfit_result=outfit_result,
        user_request=user_request,
        wardrobe_count=wardrobe_count
    )


# ==========================================
# START APPLICATION
# ==========================================

init_db()

if __name__ == "__main__":
    app.run(debug=True)
