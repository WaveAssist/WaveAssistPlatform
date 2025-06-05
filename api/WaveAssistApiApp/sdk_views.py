
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
import WaveAssistApiApp.Utils.validator as validator
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.Utils.utils import get_param
from .models import User, Project
import json
from django.views.decorators.http import require_POST

@require_POST
def send_email(request):
    try:
        # Validate user and project access
        success, message, user_object, project_object = validator.validate_user_and_project(request, READ_GTE)

        if not success:
            return ResponseParser.getParsedErrorMessage(message)

        # Extract required POST params
        to_email = get_param(request, "to_email")
        subject = get_param(request, "subject")
        html_content = get_param(request, "html_content")
        from_email = DEFAULT_FROM_EMAIL

        if not all([to_email, subject, html_content]):
            return ResponseParser.getParsedErrorMessage("Missing one or more required fields: to_email, subject, html_content")

        # Send email via SendGrid
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

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
