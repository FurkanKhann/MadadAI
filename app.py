from flask import Flask, redirect, url_for, session, render_template
from auth.routes import auth_bp
from invoice.routes import invoice_bp
import os

app = Flask(__name__)
app.secret_key = "madad-ai-invoice-system-2025"

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(invoice_bp, url_prefix="/invoice")

@app.route("/")
def home():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    # Check if user is logged in
    if session.get("user_id"):
        return render_template("main_dashboard.html", title="Madad AI - Dashboard")
    else:
        return redirect(url_for("auth.login"))

# Make session available in all templates
@app.context_processor
def inject_user():
    return dict(session=session)

if __name__ == "__main__":
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # Production server (when deployed)
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
