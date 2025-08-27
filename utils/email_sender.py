import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Optional

class EmailSender:
    def __init__(self, smtp_server: str, smtp_port: int, email: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
    
    def send_invoice_email(self, to_email: str, subject: str, body: str, attachment_path: Optional[str] = None) -> bool:
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )
                msg.attach(part)
            
            # Connect to server and send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False

def get_email_template(invoice_data: dict, company_data: dict) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .invoice-header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .company-name {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
            .invoice-details {{ margin: 20px 0; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="invoice-header">
            <div class="company-name">{company_data.get('company_name', 'Your Company')}</div>
            <p>Invoice #{invoice_data.get('invoice_number', 'N/A')}</p>
        </div>
        
        <div class="invoice-details">
            <p>Dear {invoice_data.get('client_name', 'Client')},</p>
            
            <p>Please find attached your invoice for the amount of <strong>Rs. {invoice_data.get('total_amount', '0.00')}</strong>.</p>
            
            <p><strong>Invoice Details:</strong></p>
            <ul>
                <li>Invoice Number: {invoice_data.get('invoice_number', 'N/A')}</li>
                <li>Date Issued: {invoice_data.get('date_issued', 'N/A')}</li>
                <li>Due Date: {invoice_data.get('due_date', 'N/A')}</li>
                <li>Total Amount: Rs. {invoice_data.get('total_amount', '0.00')}</li>
            </ul>
            
            <p>Payment is due by {invoice_data.get('due_date', 'the due date')}. Please remit payment at your earliest convenience.</p>
            
            <p>If you have any questions regarding this invoice, please don't hesitate to contact us.</p>
            
            <p>Thank you for your business!</p>
        </div>
        
        <div class="footer">
            <p>Best regards,<br>
            {company_data.get('company_name', 'Your Company')}<br>
            {company_data.get('email', '')}<br>
            {company_data.get('phone', '')}</p>
        </div>
    </body>
    </html>
    """
