from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from config import supabase

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # If already logged in, redirect to dashboard
    if session.get("user_id"):
        return redirect(url_for("invoice.dashboard"))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            if res and getattr(res, "user", None):
                flash("Account created successfully. Please log in.", "success")
                return redirect(url_for("auth.login"))
            flash("Could not create account.", "error")
        except Exception as e:
            flash(str(e), "error")
    return render_template("signup.html", title="Sign Up - Madad AI")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, redirect to dashboard
    if session.get("user_id"):
        return redirect(url_for("invoice.dashboard"))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res and getattr(res, "user", None):
                # persist minimal info in Flask session
                session["user_email"] = email
                session["user_id"] = res.user.id
                flash("Welcome back to Madad AI!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid credentials.", "error")
        except Exception as e:
            flash(str(e), "error")
    return render_template("login.html", title="Login - Madad AI")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
