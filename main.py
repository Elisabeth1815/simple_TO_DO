from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm
from datetime import date
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# Flask-login
login_manager = LoginManager()
login_manager.init_app(app)

# Create and connect to DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///users_tasks.db")
db = SQLAlchemy()
db.init_app(app)


# Retrieve a user from the database based on e-mail
@login_manager.user_loader
def load_user(user_id):
	return db.get_or_404(User, user_id)


class Task(db.Model):
	__tablename__ = "tasks"
	id = db.Column(db.Integer, primary_key=True)
	# user.id refers to the table name of the User class
	author_id = db.Column(db.Integer, db.ForeignKey("users_tasks.id"))
	author = relationship("User", back_populates="tasks")
	task = db.Column(db.Text, nullable=False)


# User table for registered users
class User(UserMixin, db.Model):
	__tablename__ = "users_tasks"
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100))
	email = db.Column(db.String(100), unique=True)
	password = db.Column(db.String(100))
	tasks = relationship("Task", back_populates="author")


with app.app_context():
	db.create_all()


@app.route('/register', methods=["GET", "POST"])
def register():
	form = RegisterForm()
	if form.validate_on_submit():

		# if e-mail is already in DB
		result = db.session.execute(db.select(User).where(User.email == form.email.data))
		user = result.scalar()

		# if user already exists
		if user:
			flash("You've already signed up with this e-mail.")
			return redirect(url_for('login'))

		hash_and_salted_password = generate_password_hash(
			form.password.data,
			method='pbkdf2:sha256',
			salt_length=8
		)
		new_user = User(
			name=form.name.data,
			email=form.email.data,
			password=hash_and_salted_password,
		)
		db.session.add(new_user)
		db.session.commit()

		login_user(new_user)

		return redirect(url_for("home"))

	return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		password = form.password.data
		result = db.session.execute(db.select(User).where(User.email == form.email.data))
		user = result.scalar()
		# if e-mail does not exist
		if not user:
			flash("This e-mail does not exist. Please try again.")
			return redirect(url_for('login'))
		# if password is incorrect
		elif not check_password_hash(user.password, password):
			flash("Your password is incorrect. Please try again.")
			return redirect(url_for('login'))
		else:
			login_user(user)
			return redirect(url_for('home'))
	return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('home'))


@app.route('/tasks_today', methods=["GET", "POST"])
def tasks_today():
	result = db.session.execute(db.select(Task))
	tasks = result.scalars().all()

	d = date.today()
	today = d.strftime("%d.%m.%Y")

	return render_template("tasks_today.html", all_tasks=tasks, current_user=current_user, today=today)


@app.route('/add_task', methods=["GET", "POST"])
def add_new_task():
	if request.method == 'POST':
		if request.form.get('add_task') == 'add_task':
			new_task = Task(
				author=current_user,
				task=request.form["task"],
			)
			db.session.add(new_task)
			db.session.commit()
			return redirect(url_for('tasks_today'))
		elif request.form.get('delete_') == 'delete_':
			return redirect(url_for('add_new_task'))

		task = db.get_or_404(Task, None)

	return render_template("add_task.html", current_user=current_user)


@app.route("/delete_task")
def delete_task():
	task_id = request.args.get('id')
	task_to_delete = db.get_or_404(Task, task_id)
	db.session.delete(task_to_delete)
	db.session.commit()
	return redirect(url_for('tasks_today'))


@app.route("/delete_tasks")
def delete_tasks():
	tasks = db.session.query(Task).filter(Task.author_id == current_user.id).delete()
	db.session.commit()
	return redirect(url_for('tasks_today', tasks=tasks))


@app.route("/edit", methods=["GET", "POST"])
def edit_task():
	if request.method == "POST":
		task_id = request.form["id"]
		task_to_update = db.get_or_404(Task, task_id)
		task_to_update.task = request.form["task"]
		db.session.commit()
		return redirect(url_for('tasks_today'))
	task_id = request.args.get('id')
	task_edited = db.get_or_404(Task, task_id)
	return render_template("edit_task.html", task=task_edited, current_user=current_user)


@app.route('/')
def home():
	return render_template("index.html", current_user=current_user)


if __name__ == "__main__":
	app.run(debug=False)
