import pygame
import random
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.String(150), nullable=True)
    ingredients = db.Column(db.Text, nullable=False)
    process = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(150))
    source = db.Column(db.String(250), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    votes_interesting = db.Column(db.Integer, default=0)
    votes_mindblowing = db.Column(db.Integer, default=0)
    votes_false = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(username=username, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def index():
    category = request.args.get('category')
    search = request.args.get('search')
    tag = request.args.get('tag')
    query = Recipe.query

    if category and category != 'all':
        query = query.filter_by(category=category)

    if tag:
        query = query.filter(Recipe.tags.contains(tag))

    if search:
        query = query.filter(Recipe.title.contains(search))

    recipes = query.order_by(Recipe.id.desc()).all()
    return render_template('index.html', recipes=recipes, selected_category=category)

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return render_template('recipe_detail.html', recipe=recipe)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        tags = request.form.get('tags', '')
        ingredients = request.form['ingredients']
        process = request.form['process']
        source = request.form.get('source', '')
        image_file = request.files['image']
        filename = secure_filename(image_file.filename)
        if filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
        else:
            filename = ''

        new_recipe = Recipe(
            title=title,
            category=category,
            tags=tags,
            ingredients=ingredients,
            process=process,
            image=filename,
            source=source,
            user_id=current_user.id
        )
        db.session.add(new_recipe)
        db.session.commit()
        flash('Recipe added!')
        return redirect(url_for('index'))
    return render_template('add_recipe.html')

@app.route('/edit/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        flash("You don't have permission to edit this recipe.")
        return redirect(url_for('index'))
    if request.method == 'POST':
        recipe.title = request.form['title']
        recipe.category = request.form['category']
        recipe.tags = request.form.get('tags', '')
        recipe.ingredients = request.form['ingredients']
        recipe.process = request.form['process']
        recipe.source = request.form.get('source', '')
        db.session.commit()
        flash('Recipe updated successfully!')
        return redirect(url_for('recipe_detail', recipe_id=recipe.id))
    return render_template('edit_recipe.html', recipe=recipe)

@app.route('/delete/<int:recipe_id>')
@login_required
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        flash("You don't have permission to delete this recipe.")
        return redirect(url_for('index'))
    db.session.delete(recipe)
    db.session.commit()
    flash('Recipe deleted successfully!')
    return redirect(url_for('index'))

@app.route('/my_recipes')
@login_required
def my_recipes():
    recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.id.desc()).all()
    return render_template('my_recipes.html', recipes=recipes)

@app.route('/vote/<int:recipe_id>/<vote_type>')
@login_required
def vote(recipe_id, vote_type):
    recipe = Recipe.query.get_or_404(recipe_id)
    if vote_type == 'interesting':
        recipe.votes_interesting += 1
    elif vote_type == 'mindblowing':
        recipe.votes_mindblowing += 1
    elif vote_type == 'false':
        recipe.votes_false += 1
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
