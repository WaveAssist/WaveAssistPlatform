
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

MAX_FILE_SIZE_MB = 5
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

        # Build the email message
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        # Add attachment if present
        if attachment_file:
            if attachment_file.size > MAX_FILE_SIZE_BYTES:
                return ResponseParser.getParsedErrorMessage(
                    f"Attachment too large. Max size is {MAX_FILE_SIZE_MB} MB."
                )

            file_data = attachment_file.read()
            encoded_file = base64.b64encode(file_data).decode()

            # Guess MIME type from filename
            mime_type, _ = mimetypes.guess_type(attachment_file.name)
            mime_type = mime_type or "application/octet-stream"  # Fallback if unknown

            attached_file = Attachment(
                FileContent(encoded_file),
                FileName(attachment_file.name),
                FileType(mime_type),
                Disposition("attachment")
            )
            message.attachment = attached_file

        # Send the email
        sg = SendGridAPIClient(SEND_GRID_KEY)
        response = sg.send(message)

        if 200 <= response.status_code < 300:
            return ResponseParser.getParsedSuccessMessage(
                {"status": "sent", "to_email": to_email},
                '200',
                "Email sent successfully."
            )
        else:
            return ResponseParser.getParsedErrorMessage(
                f"Failed to send email. Status code: {response.status_code}, Body: {response.body.decode('utf-8')}"
            )

    except Exception as e:
        utils.logger.error(f"❌ Error in send_email API: {str(e)}")
        return ResponseParser.getParsedErrorMessage("Server error while sending email")
