
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
import WaveAssistApiApp.Utils.validator as validator
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.Utils.utils import get_param
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
import mimetypes
import base64
from postmarker.core import PostmarkClient

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@require_POST
def send_email(request):
    try:
        # Validate user and project access
        success, message, user_object, project_object = validator.validate_user_and_project(request, READ_GTE)

        if not success:
            return ResponseParser.getParsedErrorMessage(message)

        # Extract required POST params
        subject = get_param(request, "subject")
        html_content = get_param(request, "html_content")
        attachment_file = request.FILES.get("attachment")  # <-- expecting uploaded file in form-data
        from_email = DEFAULT_FROM_EMAIL

        if not all([subject, html_content]):
            return ResponseParser.getParsedErrorMessage("Missing one or more required fields: subject, html_content")

        try:
            to_email = str(user_object.username).strip()
            validate_email(to_email)
        except Exception as e:
            return ResponseParser.getParsedErrorMessage("Invalid recipient email address.")

        # Prepare Postmark client
        client = PostmarkClient(server_token=POSTMARK_API_TOKEN)

        # Build attachment if present
        attachments = []
        if attachment_file:
            if attachment_file.size > MAX_FILE_SIZE_BYTES:
                return ResponseParser.getParsedErrorMessage(
                    f"Attachment too large. Max size is {MAX_FILE_SIZE_MB} MB."
                )
            file_data = attachment_file.read()
            encoded_file = base64.b64encode(file_data).decode()
            mime_type, _ = mimetypes.guess_type(attachment_file.name)
            mime_type = mime_type or "application/octet-stream"

            attachments.append({
                "Name": attachment_file.name,
                "Content": encoded_file,
                "ContentType": mime_type,
                "ContentID": None
            })


        try:
            # Send the email
            client.emails.send(
                From=from_email,
                To=to_email,
                Subject=subject,
                HtmlBody=html_content,
                Attachments=attachments if attachments else None
            )
            return ResponseParser.getParsedSuccessMessage(
                {"status": "sent", "to_email": to_email},
                '200',
                "Email sent successfully via Postmark."
            )
        except:
            send_email_backup(from_email=from_email,
                              to_emails=to_email,
                              subject=subject,
                              html_content=html_content)
            return ResponseParser.getParsedSuccessMessage(
                {"status": "sent_backup", "to_email": to_email},
                '200',
                "Email sent via backup method due to Postmark failure."
            )
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Error sending email: {str(e)}")

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email_backup(from_email,
                      to_emails,
                      subject,
                      html_content) -> None:
    try:
        # Normalize recipients to a list
        recipients = [to_emails] if isinstance(to_emails, str) else list(to_emails)

        # Build the message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        # Connect to Gmail SMTP and send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(MAILER_LOGIN_EMAIL, MAILER_LOGIN_EMAIL_PASSWORD)
        server.sendmail(from_email, recipients, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {recipients}")
    except Exception as e:
        print(f"Failed to send email: {e}")

