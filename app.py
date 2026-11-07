from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
from models import User, StaffProfile, Trek, Booking
from routes.auth import auth
from routes.admin import admin
from routes.staff import staff
from routes.trekker import trekker

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"

app.register_blueprint(auth)
app.register_blueprint(admin)
app.register_blueprint(staff)
app.register_blueprint(trekker)

#user loader callback for flask login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/")
def index():
    return render_template("index.html")

# Create database tables inside application context
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
