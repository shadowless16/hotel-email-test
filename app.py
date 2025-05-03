# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
import logging # Import logging
import smtplib # Import smtplib to catch its specific errors

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
# Secret Key: Essential for session management (flash messages)
app.secret_key = os.getenv('SECRET_KEY', 'a-very-strong-dev-secret-key-should-be-set-in-env')

# Flask-Mail Configuration: Load from .env or use defaults
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't', 'yes')
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't', 'yes')
# Default sender: Use specific sender from .env, fallback to MAIL_USERNAME
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
# Hotel's receiving email address
app.config['HOTEL_EMAIL'] = os.getenv('HOTEL_EMAIL')
# Optional: Define Hotel Name for emails
app.config['HOTEL_NAME'] = os.getenv('HOTEL_NAME', 'Our Hotel') # Add HOTEL_NAME to .env or use default

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
app.logger.setLevel(logging.INFO)

# --- Configuration Checks ---
required_configs = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER', 'HOTEL_EMAIL']
missing_configs = [config for config in required_configs if not app.config.get(config)]
if missing_configs:
    app.logger.warning(f"Missing required MAIL configurations in .env file: {', '.join(missing_configs)}. Email functionality may fail.")

# --- Initialize Extensions ---
mail = Mail(app)

# --- Routes ---
@app.route('/')
def index():
    """Renders the booking form page."""
    return render_template('booking_form.html')

@app.route('/submit_booking', methods=['POST'])
def submit_booking():
    """Handles booking form submission, validates data, and sends emails."""
    # Get form data safely
    guest_name = request.form.get('guest_name', '').strip()
    guest_email = request.form.get('guest_email', '').strip()
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    room_type = request.form.get('room_type')
    guests = request.form.get('guests')
    special_requests = request.form.get('special_requests', 'None').strip()

    # --- Basic Server-Side Validation ---
    required_fields = {
        'Full Name': guest_name,
        'Email': guest_email,
        'Check-in Date': check_in,
        'Check-out Date': check_out,
        'Room Type': room_type,
        'Number of Guests': guests
    }
    missing_fields = [name for name, value in required_fields.items() if not value]
    if missing_fields:
        flash(f"Please fill out all required fields: {', '.join(missing_fields)}.", 'warning')
        # Optionally, pass back form data to repopulate the form
        return redirect(url_for('index'))
    # Add more validation (e.g., email format, date logic) if needed

    # --- Email Sending Logic ---
    hotel_name = app.config['HOTEL_NAME']
    try:
        # --- Email to Hotel ---
        hotel_subject = f"New Booking Request: {guest_name} - {room_type} ({check_in} to {check_out})"
        hotel_msg = Message(
            subject=hotel_subject,
            recipients=[app.config['HOTEL_EMAIL']],
            sender=(hotel_name, app.config['MAIL_DEFAULT_SENDER']) # Set sender name
        )
        # Use a more structured body
        hotel_msg.body = f"""
Dear Hotel Team,

A new booking request has been submitted through the website.

Guest Information:
------------------
Name:          {guest_name}
Email:         {guest_email}

Booking Details:
------------------
Room Type:     {room_type}
Check-in Date: {check_in}
Check-out Date:{check_out}
Num. Guests:   {guests}

Special Requests:
------------------
{special_requests if special_requests else 'None provided.'}

Next Steps:
-----------
Please review this request for availability and contact the guest ({guest_email}) directly to confirm the booking or discuss alternatives.

Thank you.
        """
        app.logger.info(f"Attempting to send booking request email to {app.config['HOTEL_EMAIL']} with subject: {hotel_subject}")
        mail.send(hotel_msg)
        app.logger.info("Booking request email sent successfully to hotel.")

        # --- Confirmation Email to Guest ---
        guest_subject = f"Booking Request Received - {hotel_name}"
        guest_msg = Message(
            subject=guest_subject,
            recipients=[guest_email],
            sender=(hotel_name, app.config['MAIL_DEFAULT_SENDER']) # Set sender name
        )
        guest_msg.body = f"""
Dear {guest_name},

Thank you for submitting your booking request for {hotel_name}!

We have received the following details:
-------------------------------------
Room Type:     {room_type}
Check-in Date: {check_in}
Check-out Date:{check_out}
Num. Guests:   {guests}
Special Requests: {special_requests if special_requests else 'None provided.'}

Please Note:
------------
This email confirms that we have received your request. It is *not* a final booking confirmation.

Our team will review availability based on your request and will contact you via email ({guest_email}) within [Specify Timeframe, e.g., 24 hours] to either confirm your booking or discuss alternative options if your requested room/dates are unavailable.

If you have urgent questions, please feel free to contact us directly at [Hotel Phone Number] or reply to this email.

We look forward to potentially welcoming you!

Best regards,

The Team at {hotel_name}
[Optional: Hotel Website Link]
        """
        app.logger.info(f"Attempting to send confirmation email to {guest_email} with subject: {guest_subject}")
        mail.send(guest_msg)
        app.logger.info("Confirmation email sent successfully to guest.")

        flash('Booking request submitted successfully! Please check your email (including spam folder) for details. We will contact you soon to confirm availability.', 'success')

    # --- Specific Error Handling ---
    except TimeoutError as e:
        app.logger.error(f"Mail Server Connection Timeout: {e}. Check network, firewall, and MAIL_SERVER/PORT ({app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}).", exc_info=True)
        flash(f"Could not connect to the mail server (Timeout). Please check your internet connection and firewall settings. Error: {e}", 'danger')
    except smtplib.SMTPConnectError as e:
        app.logger.error(f"SMTP Connection Error: {e}. Check MAIL_SERVER and MAIL_PORT.", exc_info=True)
        flash(f"Failed to connect to the mail server ({app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}). Ensure settings are correct and the server is reachable. Error: {e}", 'danger')
    except smtplib.SMTPAuthenticationError as e:
        app.logger.error(f"SMTP Authentication Error: {e}. Check MAIL_USERNAME and MAIL_PASSWORD (use App Password for Gmail).", exc_info=True)
        flash(f"Authentication failed with the mail server. Check email username and password/app password. Error: {e}", 'danger')
    except smtplib.SMTPSenderRefused as e:
        app.logger.error(f"SMTP Sender Refused: {e}. Check MAIL_DEFAULT_SENDER ('{app.config['MAIL_DEFAULT_SENDER']}').", exc_info=True)
        flash(f"Mail server refused the sender address ('{app.config['MAIL_DEFAULT_SENDER']}'). Check configuration. Error: {e}", 'danger')
    except ConnectionRefusedError as e:
        app.logger.error(f"Mail Server Connection Refused: {e}. Check MAIL_SERVER and MAIL_PORT.", exc_info=True)
        flash('The mail server actively refused the connection. Check server address/port and ensure the mail server is running.', 'danger')
    except Exception as e: # Catch any other unexpected exceptions
        app.logger.error(f"An unexpected error occurred during email sending: {e}", exc_info=True) # Log full traceback
        flash(f'An unexpected error occurred ({type(e).__name__}). Please try again later or contact support.', 'danger')

    # Redirect back to the index page regardless of email success/failure (flash message indicates status)
    return redirect(url_for('index'))

# --- Main Execution ---
if __name__ == '__main__':
    # Important: Set debug=False in a production environment!
    # host='0.0.0.0' makes the server accessible on your network. Ensure firewall allows port 5000.
    app.run(debug=True, host='0.0.0.0', port=5000)
