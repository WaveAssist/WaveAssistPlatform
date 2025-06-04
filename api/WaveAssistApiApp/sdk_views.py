
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
import WaveAssistApiApp.Utils.validator as validator
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.Utils.utils import get_param
from .models import User, Project


def send_email(request):
    try:
        uid = get_param(request, 'uid')
        try:
            user_object = User.objects.get(uid=uid)
        except:
            return ResponseParser.getParsedErrorMessage('User not found')

        project_key = get_param(request, 'project_key')
        try:
            project_object = Project.objects.get(project_key=project_key)
        except:
            return ResponseParser.getParsedErrorMessage('Project not found')

        # Extract required POST params
        to_email = get_param(request, "to_email")
        subject = get_param(request, "subject")
        html_content = get_param(request, "html_content")
        from_email = get_param(request, "from_email") or DEFAULT_FROM_EMAIL

        if not all([to_email, subject, html_content]):
            return ResponseParser.getParsedErrorMessage("Missing one or more required fields: to_email, subject, html_content")

        if not from_email:
            return ResponseParser.getParsedErrorMessage("Sender email not configured. Pass 'from_email' or set 'DEFAULT_FROM_EMAIL'.")

        sendgrid_api_key = SEND_GRID_KEY
        if not sendgrid_api_key:
            return ResponseParser.getParsedErrorMessage("SENDGRID_API_KEY is not configured on the server.")

        # Send email via SendGrid
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        sg = SendGridAPIClient(sendgrid_api_key)
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
