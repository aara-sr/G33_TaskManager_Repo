from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=1)
    due_date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8),
        Regexp(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must contain at least one uppercase letter, one number, and one special character')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('New Password', validators=[
        Length(min=8),
        Regexp(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', message='Password must contain at least one uppercase letter, one number, and one special character')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('password')])
    submit = SubmitField('Update Profile')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/business')
def business():
    return render_template('business.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Email already exists. Please use a different email.', 'danger')
            return render_template('register.html', title='Register', form=form)

        
        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash('Username already taken. Please choose another one.', 'danger')
            return render_template('register.html', title='Register', form=form)

        
        existing_password = User.query.filter_by(password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')).first()
        if existing_password:
            flash('This password is already in use. Please choose a different one.', 'danger')
            return render_template('register.html', title='Register', form=form)

        
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)

        
        db.session.add(new_user)
        db.session.commit()

        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    search_query = request.args.get('search', '')
    tasks = Task.query.filter_by(user_id=current_user.id)
    if search_query:
        tasks = tasks.filter(Task.title.contains(search_query) | Task.description.contains(search_query))
    tasks = tasks.order_by(Task.priority.desc(), Task.due_date).all()
    return render_template('dashboard.html', tasks=tasks, search_query=search_query)

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form['title']
    description = request.form['description']
    priority = int(request.form['priority'])
    due_date_str = request.form['due_date']
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
    new_task = Task(title=title, description=description, priority=priority, due_date=due_date, user_id=current_user.id)
    db.session.add(new_task)
    db.session.commit()
    flash('Task added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/update_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.completed:
        flash('Completed tasks cannot be updated.', 'warning')
        return redirect(url_for('dashboard'))
    if task.user_id != current_user.id:
        flash('You are not authorized to update this task', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.priority = int(request.form['priority'])
        due_date_str = request.form['due_date']
        task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('update_task.html', task=task)

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('You are not authorized to complete this task', 'danger')
        return redirect(url_for('dashboard'))
    task.completed = True
    db.session.commit()
    flash('Task marked as complete!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('You are not authorized to delete this task', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    
    return render_template('forgot_password.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('dashboard'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('profile.html', title='Profile', form=form)

@app.route('/filter_tasks')
@login_required
def filter_tasks():
    search_query = request.args.get('search', '')
    filter_value = request.args.get('filter', '')
    
    tasks = Task.query.filter_by(user_id=current_user.id)
    
    if search_query:
        tasks = tasks.filter(Task.title.contains(search_query) | Task.description.contains(search_query))
    
    if filter_value:
        if filter_value == 'priority_high':
            tasks = tasks.filter_by(priority=3)
        elif filter_value == 'priority_medium':
            tasks = tasks.filter_by(priority=2)
        elif filter_value == 'priority_low':
            tasks = tasks.filter_by(priority=1)
        elif filter_value == 'incomplete':
            tasks = tasks.filter_by(completed=False)
        elif filter_value == 'completed':
            tasks = tasks.filter_by(completed=True)
    
    tasks = tasks.order_by(Task.priority.desc(), Task.due_date).all()
    
    html = render_template_string('''
        {% for task in tasks %}
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title text-dark">{{ task.title }}</h5>
                    <p class="card-text text-dark">{{ task.description }}</p>
                    <p class="card-text">
                        <small class="text-muted">
                            Priority: 
                            {% if task.priority == 1 %}
                                <span class="badge bg-success">Low</span>
                            {% elif task.priority == 2 %}
                                <span class="badge bg-warning">Medium</span>
                            {% else %}
                                <span class="badge bg-danger">High</span>
                            {% endif %}
                        </small>
                    </p>
                    <p class="card-text">
                        <small class="text-muted">Due Date: {{ task.due_date.strftime('%Y-%m-%d') if task.due_date else 'Not set' }}</small>
                    </p>
                    <p class="card-text">
                        <small class="text-muted">Status: {{ 'Completed' if task.completed else 'Incomplete' }}</small>
                    </p>
                    <div class="mt-3">
                        <a href="{{ url_for('update_task', task_id=task.id) }}" class="btn btn-primary btn-sm">Update</a>
                        <a href="{{ url_for('delete_task', task_id=task.id) }}" class="btn btn-danger btn-sm">Delete</a>
                        {% if not task.completed %}
                            <a href="{{ url_for('complete_task', task_id=task.id) }}" class="btn btn-success btn-sm">Mark Complete</a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    ''', tasks=tasks)
    
    return jsonify({'html': html})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

