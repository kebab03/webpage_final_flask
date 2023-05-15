from flask import Flask, render_template, jsonify, request, session, redirect, g
import sqlite3
import os
import threading
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "your_secret_key"

# SMTP email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "kebab2803"
SMTP_PASSWORD = "eeazzvwbyctfvpkr"
SENDER_EMAIL = "kebab2803@gmail.com"

# SQLite database setup
DATABASE = "users.db"


def get_database_connection():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT)")
    return db


@app.teardown_appcontext
def close_database_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# Routes
@app.route("/", methods=["GET", "POST"])
def home():
    if "email" in session:
        return redirect("/dashboard")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if login_user(email, password):
            session["email"] = email
            return redirect("/dashboard")
        else:
            return render_template("index.html", error="Invalid email or password.")
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "email" in session:
        return redirect("/dashboard")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if register_user(email, password):
            session["email"] = email
            send_registration_email(email)
            return redirect("/dashboard")
        else:
            return render_template("register.html", error="Email already registered.")
    return render_template("register.html")


# Define global variables to store the values
saved_num_buttons = 0
saved_button_labels = []
saved_button_states = []


@app.route('/toggle', methods=['GET', 'POST'])
def toggle():
    global saved_num_buttons, saved_button_labels, saved_button_states

    if request.method == 'POST':
        num_buttons = int(request.form['num_buttons'])
        button_labels = [request.form[f'button{i+1}'] for i in range(num_buttons)]
        button_states = ['off'] * num_buttons

        saved_num_buttons = num_buttons
        saved_button_labels = button_labels
        saved_button_states = button_states

        return render_template('toggle.html', num_buttons=num_buttons, button_labels=button_labels,
                               button_states=button_states)
    else:
        if saved_num_buttons == 0:
            return render_template('toggle.html', num_buttons=1, button_labels=[], button_states=[])
        else:
            return render_template('toggle.html', num_buttons=saved_num_buttons, button_labels=saved_button_labels,
                                   button_states=saved_button_states)

@app.route('/state', methods=['POST'])
def update_state():
    global saved_button_states, saved_button_labels

    data = request.get_json()
    button_id = int(data.get('buttonId'))
    new_state = data.get('state')
    button_label = data.get('buttonLabel')

    saved_button_states[button_id] = new_state
    saved_button_labels[button_id] = button_label

    return jsonify({'message': f'State updated for button {button_label}'})

@app.route('/state', methods=['GET'])
def get_state():
    state_data = []
    for button_index, state in enumerate(saved_button_states):
        button_label = saved_button_labels[button_index]
        state_data.append({"id": button_index, "buttonLabel": button_label, "state": state})
    return jsonify({'buttons': state_data})


@app.route('/toggle-state', methods=['POST'])
def toggle_state():
    if 'email' not in session:
        return jsonify(error='Unauthorized access')

    index = int(request.json['index'])  # Get the index of the button
    button_id = f'button{index + 1}'  # Button ID based on the index

    # Toggle the state of the button
    if saved_button_states[index] == 'on':
        saved_button_states[index] = 'off'
    else:
        saved_button_states[index] = 'on'

    return jsonify(switch=saved_button_states[index])


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "email" not in session:
        return redirect("/")

    if request.method == "POST":
        num_buttons = int(request.form["num_buttons"])
        button_labels = []
        for i in range(num_buttons):
            label = request.form.get("button" + str(i + 1))
            button_labels.append(label)

        global saved_num_buttons, saved_button_labels, saved_button_states
        saved_num_buttons = num_buttons
        saved_button_labels = button_labels
        saved_button_states = ['off'] * num_buttons

    return render_template("dashboard.html", username=session["email"], num_buttons=saved_num_buttons)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("email", None)
    return redirect("/")


# Helper functions
def register_user(email, password):
    db = get_database_connection()
    cursor = db.execute("SELECT * FROM users WHERE email=?", (email,))
    if cursor.fetchone() is not None:
        return False
    db.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
    db.commit()
    return True


def login_user(email, password):
    db = get_database_connection()
    cursor = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    return cursor.fetchone() is not None


def send_registration_email(email):
    msg = MIMEText("Thank you for registering!")
    msg["Subject"] = "Registration Confirmation"
    msg["From"] = SENDER_EMAIL
    msg["To"] = email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, [email], msg.as_string())
        server.quit()
    except smtplib.SMTPException as e:
        print("Error sending email:", str(e))
        print("SMTP debug response:", server.get_debuglevel())


if __name__ == "__main__":
    app.run(debug=True)

