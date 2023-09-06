import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
class Mailer:
    def __init__(self, from_email_address="support@waveassist.io", login_password='REMOVED_CREDENTIAL'):
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.login_email_address = 'kakshil.shah@waveassist.io'
        self.login_password = login_password
        self.from_email_address = from_email_address
        self.sent_emails = []
        self.MAX_EMAILS_TO_STORE = 20


    def create_message(self, to_email_address, subject, email_body):
        message = MIMEMultipart()
        message['From'] = self.from_email_address
        message['To'] = to_email_address
        message['Subject'] = subject
        message.attach(MIMEText(email_body, 'plain'))
        return message

    def store_sent_email(self, to_email_address, subject, email_body, identifier):

        email_dict = {
            'to': to_email_address,
            'subject': subject,
            'body': email_body,
            'identifier': identifier
        }

        # Get the current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Append the sent email with timestamp to the list
        self.sent_emails.append((timestamp, email_dict))

        # Keep only the last 20 emails in the list
        if len(self.sent_emails) > self.MAX_EMAILS_TO_STORE:
            self.sent_emails = self.sent_emails[-self.MAX_EMAILS_TO_STORE:]

    def fetch_recent_emails(self):
        return self.sent_emails

    def send_email(self, to, subject, body, identifier=""):
        try:
            # Create the message
            message = self.create_message(to, subject, body)

            # Establish a secure TLS connection to the SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()

            # Log in to your email account
            server.login(self.login_email_address, self.login_password)

            # Send the email
            server.sendmail(self.from_email_address, to, message.as_string())

            self.store_sent_email(to,subject,body,identifier)
            print("Email sent successfully")

        except Exception as e:
            print("Error: Unable to send email.")
            print(e)




# Integration code:
# from Integrations.Mailer import Mailer
# mailer = Mailer()

##Usage
# mailer.send_email(to_email_address, subject, email_body)

## Fetch recent emails
# mailer.fetch_recent_emails()
