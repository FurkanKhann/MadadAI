from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from datetime import date, timedelta
from io import BytesIO
from config import supabase, current_user_id
from utils.email_sender import EmailSender, get_email_template
import uuid

invoice_bp = Blueprint("invoice", __name__, template_folder="../templates")

# ---- Helpers ----
def require_login():
    if not current_user_id():
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("auth.login"))
    return None

# ---- Dashboard ----
@invoice_bp.route("/")
def dashboard():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp
    
    # fetch or ask for company setup
    company = (
        supabase.table("companies")
        .select("*")
        .eq("user_id", current_user_id())
        .limit(1)
        .execute()
    )
    company_row = company.data[0] if company.data else None
    
    invoices = (
        supabase.table("invoices")
        .select("id, invoice_number, client_name, total_amount, date_issued, due_date")
        .in_("company_id", [company_row["id"]] if company_row else ["00000000-0000-0000-0000-000000000000"])
        .order("date_issued", desc=True)
        .execute()
    )
    
    return render_template("invoice_dashboard.html", company=company_row, invoices=invoices.data)

# ---- Company Profile ----
@invoice_bp.route("/company", methods=["GET", "POST"])
def company_profile():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp
    
    existing = (
        supabase.table("companies").select("*").eq("user_id", current_user_id()).limit(1).execute()
    )
    company = existing.data[0] if existing.data else None
    
    if request.method == "POST":
        payload = {
            "user_id": current_user_id(),
            "company_name": request.form.get("company_name"),
            "address": request.form.get("address"),
            "phone": request.form.get("phone"),
            "email": request.form.get("email"),
            "smtp_email": request.form.get("smtp_email"),
            "smtp_password": request.form.get("smtp_password"),
            "smtp_server": request.form.get("smtp_server", "smtp.gmail.com"),
            "smtp_port": int(request.form.get("smtp_port", 587)),
        }
        
        if company:
            supabase.table("companies").update(payload).eq("id", company["id"]).execute()
            flash("Company profile updated successfully!", "success")
        else:
            supabase.table("companies").insert(payload).execute()
            flash("Company profile created successfully!", "success")
        return redirect(url_for("invoice.dashboard"))
    
    return render_template("company_form.html", company=company)

# ---- Create Invoice ----
@invoice_bp.route("/new", methods=["GET", "POST"])
def new_invoice():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp
    
    company = (
        supabase.table("companies").select("*").eq("user_id", current_user_id()).limit(1).execute()
    )
    if not company.data:
        flash("Please create your company profile first.", "warning")
        return redirect(url_for("invoice.company_profile"))
    
    company = company.data[0]
    
    if request.method == "POST":
        items_desc = request.form.getlist("item_desc")
        items_qty = request.form.getlist("quantity")
        items_price = request.form.getlist("unit_price")
        
        client_name = request.form.get("client_name")
        client_email = request.form.get("client_email")
        client_address = request.form.get("client_address")
        tax_rate = float(request.form.get("tax_rate", 0) or 0)
        
        subtotal = 0.0
        for q, p in zip(items_qty, items_price):
            try:
                subtotal += int(q) * float(p)
            except ValueError:
                pass
        
        tax_amount = round(subtotal * (tax_rate / 100.0), 2)
        total_amount = round((subtotal + tax_amount) * 100, 2)  # Convert to Rs.
        
        invoice_number = request.form.get("invoice_number") or f"INV-{str(uuid.uuid4())[:8].upper()}"
        today = date.today()
        due = today + timedelta(days=30)
        
        # Insert invoice
        inv_res = supabase.table("invoices").insert({
            "company_id": company["id"],
            "client_name": client_name,
            "client_email": client_email,
            "client_address": client_address,
            "invoice_number": invoice_number,
            "date_issued": today.isoformat(),
            "due_date": due.isoformat(),
            "tax_rate": tax_rate,
            "total_amount": total_amount,
        }).execute()
        
        invoice_id = inv_res.data[0]["id"]
        
        # Insert items
        rows = []
        for d, q, p in zip(items_desc, items_qty, items_price):
            try:
                q_i = int(q); p_f = float(p)
            except ValueError:
                continue
            rows.append({
                "invoice_id": invoice_id,
                "description": d,
                "quantity": q_i,
                "unit_price": p_f,
                "line_total": round(q_i * p_f, 2),
            })
        
        if rows:
            supabase.table("invoice_items").insert(rows).execute()
        
        flash("Invoice created successfully!", "success")
        return redirect(url_for("invoice.view_invoice", invoice_id=invoice_id))
    
    return render_template("invoice_form.html")

# ---- View Invoice ----
@invoice_bp.route("/view/<invoice_id>")
def view_invoice(invoice_id: str):
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp
    
    try:
        inv = supabase.table("invoices").select("*").eq("id", invoice_id).single().execute()
        items = supabase.table("invoice_items").select("*").eq("invoice_id", invoice_id).execute()
        company = (
            supabase.table("companies").select("*").eq("id", inv.data["company_id"]).single().execute()
        )
        
        return render_template("invoice_view.html", invoice=inv.data, items=items.data, company=company.data)
    except Exception as e:
        flash("Invoice not found.", "error")
        return redirect(url_for("invoice.dashboard"))

# ---- Send Invoice Email ----
@invoice_bp.route("/send_email/<invoice_id>", methods=["POST"])
def send_invoice_email(invoice_id: str):
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp
    
    try:
        # Get invoice and company data
        inv = supabase.table("invoices").select("*").eq("id", invoice_id).single().execute()
        company = supabase.table("companies").select("*").eq("id", inv.data["company_id"]).single().execute()
        
        # Check if email configuration exists
        if not company.data.get("smtp_email") or not company.data.get("smtp_password"):
            flash("Please configure your email settings in Company Profile first.", "error")
            return redirect(url_for("invoice.view_invoice", invoice_id=invoice_id))
        
        # Create email sender
        email_sender = EmailSender(
            smtp_server=company.data.get("smtp_server", "smtp.gmail.com"),
            smtp_port=company.data.get("smtp_port", 587),
            email=company.data["smtp_email"],
            password=company.data["smtp_password"]
        )
        
        # Generate email content
        subject = f"Invoice {inv.data['invoice_number']} from {company.data['company_name']}"
        body = get_email_template(inv.data, company.data)
        
        # Send email
        success = email_sender.send_invoice_email(
            to_email=inv.data["client_email"],
            subject=subject,
            body=body
        )
        
        if success:
            flash("Invoice sent successfully!", "success")
        else:
            flash("Failed to send invoice. Please check your email settings.", "error")
            
    except Exception as e:
        flash(f"Error sending email: {str(e)}", "error")
    
    return redirect(url_for("invoice.view_invoice", invoice_id=invoice_id))
