
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
import WaveAssistApiApp.Utils.validator as validator
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.Utils.utils import get_param, fetch_credits_from_openrouter, get_email_template_credits_limit_reached
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.utils import timezone
import mimetypes
import base64
import requests
from postmarker.core import PostmarkClient
from .models import Account

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Cap on extra (cc + bcc) recipients per send. The primary To is always the account owner;
# this bounds the blast radius so the endpoint can't be used as an open relay.
MAX_EXTRA_RECIPIENTS = 50


def _parse_recipients(raw, exclude=None):
    """Parse a comma-separated recipient string into a clean, deduped, validated list.

    Validates each address (Django email format), strips whitespace, and drops blanks,
    invalid addresses, and case-insensitive duplicates — preserving order. Addresses whose
    lowercased form is in ``exclude`` are also dropped (used to keep cc/bcc from repeating
    the owner, and bcc from repeating cc). Returns an empty list for falsy input."""
    if not raw:
        return []
    seen = set(exclude or set())
    out = []
    for part in str(raw).split(","):
        addr = part.strip()
        if not addr or addr.lower() in seen:
            continue
        try:
            validate_email(addr)
        except Exception:
            continue
        seen.add(addr.lower())
        out.append(addr)
    return out


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

        # Optional cc/bcc copies (owner is always the primary To). Each address is validated,
        # deduped, and cross-deduped so no one is mailed twice: cc excludes the owner, and bcc
        # excludes both the owner and anyone already on cc.
        owner_key = {to_email.lower()}
        cc_list = _parse_recipients(get_param(request, "cc"), exclude=owner_key)
        bcc_list = _parse_recipients(
            get_param(request, "bcc"),
            exclude=owner_key | {a.lower() for a in cc_list},
        )
        if len(cc_list) + len(bcc_list) > MAX_EXTRA_RECIPIENTS:
            return ResponseParser.getParsedErrorMessage(
                f"Too many cc/bcc recipients (max {MAX_EXTRA_RECIPIENTS})."
            )

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
            # Send the email. Cc/Bcc are only included when present (Postmark wants
            # comma-separated strings) so the owner-only path is byte-for-byte unchanged.
            send_kwargs = dict(
                From=from_email,
                To=to_email,
                Subject=subject,
                HtmlBody=html_content,
                TrackOpens=True,
                Attachments=attachments if attachments else None,
            )
            if cc_list:
                send_kwargs["Cc"] = ",".join(cc_list)
            if bcc_list:
                send_kwargs["Bcc"] = ",".join(bcc_list)
            client.emails.send(**send_kwargs)
            return ResponseParser.getParsedSuccessMessage(
                {"status": "sent", "to_email": to_email, "cc": cc_list, "bcc": bcc_list},
                '200',
                "Email sent successfully via Postmark."
            )
        except Exception as primary_error:
            # Postmark failed — try the SMTP backup. If THAT also fails we must report an
            # error, not success: a fake 200 here means silent data loss and defeats the
            # SDK's retry logic.
            backup_sent = send_email_backup(from_email=from_email,
                                            to_emails=to_email,
                                            subject=subject,
                                            html_content=html_content,
                                            cc=cc_list,
                                            bcc=bcc_list)
            if not backup_sent:
                return ResponseParser.getParsedErrorMessage(
                    f"Email send failed via both Postmark and backup: {str(primary_error)}"
                )
            return ResponseParser.getParsedSuccessMessage(
                {"status": "sent_backup", "to_email": to_email, "cc": cc_list, "bcc": bcc_list},
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
                      html_content,
                      cc=None,
                      bcc=None) -> bool:
    """SMTP fallback. Returns True if the send succeeded, False otherwise — callers must
    check the result; a False from here means the email was NOT delivered by either path."""
    try:
        # Normalize recipients to lists
        to_list = [to_emails] if isinstance(to_emails, str) else list(to_emails)
        cc_list = list(cc or [])
        bcc_list = list(bcc or [])

        # Build the message. Cc is a visible header; Bcc is NOT a header (it stays hidden)
        # but must still appear in the SMTP envelope so the server delivers to it.
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(to_list)
        if cc_list:
            msg['Cc'] = ', '.join(cc_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        envelope_recipients = to_list + cc_list + bcc_list

        # Connect to Gmail SMTP and send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(MAILER_LOGIN_EMAIL, MAILER_LOGIN_EMAIL_PASSWORD)
        server.sendmail(from_email, envelope_recipients, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {envelope_recipients}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def _send_credits_notification(to_email, assistant_name, required_credits, credits_remaining, plan_name=""):
    """Send a one-time credit limit reached email for this account."""
    try:
        subject = f"{assistant_name} - Credit Limit Reached"
        html_content = get_email_template_credits_limit_reached(
            assistant_name=assistant_name,
            required_credits=required_credits,
            credits_remaining=credits_remaining,
            plan_name=plan_name,
        )
        client = PostmarkClient(server_token=POSTMARK_API_TOKEN)
        client.emails.send(
            From=DEFAULT_FROM_EMAIL,
            To=to_email,
            Subject=subject,
            HtmlBody=html_content,
            TrackOpens=True,
        )
        utils.logger.info(f"Credits notification email sent to {to_email}")
    except Exception as e:
        utils.logger.warning(f"Postmark failed for credits notification, trying backup: {e}")
        # Best-effort internal notification: a dual failure is logged, not raised, but we
        # must check the return value — send_email_backup reports failure as False.
        if not send_email_backup(
            from_email=DEFAULT_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        ):
            utils.logger.error(f"Credits notification email failed entirely (Postmark: {e})")


@require_POST
def check_account_credits(request):
    """
    Account-level credit check with caching.
    Returns credits_available and whether a notification email should be sent.
    Caching avoids hammering OpenRouter on every agent run.
    Interval drops to FAST after payment so agents recover quickly once credits reflect.
    """
    try:
        success, message, user_object, project_object = validator.validate_user_and_project(request, READ_GTE)
        if not success:
            return ResponseParser.getParsedErrorMessage(message)

        required_credits = float(get_param(request, "required_credits") or 0)
        assistant_name = get_param(request, "assistant_name") or "Your Assistant"

        try:
            account = Account.objects.get(created_by_user=user_object)
        except Account.DoesNotExist:
            return ResponseParser.getParsedErrorMessage("Account not found.")

        if not account.open_router_key:
            return ResponseParser.getParsedErrorMessage("OpenRouter key not found.")

        now = timezone.now()
        is_stale = (
            account.credits_last_checked is None
            or (now - account.credits_last_checked).total_seconds() > account.credits_check_interval
        )

        if is_stale:
            try:
                credit_data = fetch_credits_from_openrouter(account.open_router_key)
                # Store and use WaveAssist credits (OpenRouter $ * multiplier), same as dashboard.
                new_credits_remaining = round(
                    credit_data["limit_remaining"] * WAVEASSIST_CREDIT_MULTIPLIER, 2
                )

                # If we're in fast-check mode (post-payment) and credits are now positive,
                # the payment has reflected — reset back to default interval and clear the
                # notification flag so future exhaustion triggers a fresh email.
                if account.credits_check_interval == CREDITS_CHECK_INTERVAL_FAST and new_credits_remaining > 0:
                    account.credits_check_interval = CREDITS_CHECK_INTERVAL_DEFAULT
                    account.credits_notification_sent = False

                account.credits_remaining = new_credits_remaining
                account.credits_last_checked = now
                account.save()

            except Exception as e:
                utils.logger.warning(f"Failed to fetch OpenRouter credits: {e}")
                # Fall back to cached value if available
                if account.credits_remaining is None:
                    return ResponseParser.getParsedErrorMessage(
                        "Unable to determine credit balance — OpenRouter unreachable and no cached value."
                    )

        credits_available = account.credits_remaining >= required_credits

        if not credits_available and not account.credits_notification_sent:
            account.credits_notification_sent = True
            account.save()
            _send_credits_notification(
                to_email=user_object.username,
                assistant_name=assistant_name,
                required_credits=required_credits,
                credits_remaining=account.credits_remaining,
                plan_name=account.plan_name or "",
            )

        return ResponseParser.getParsedSuccessMessage(
            {
                "credits_available": credits_available,
                "credits_remaining": account.credits_remaining,
            },
            "200",
            "Credits checked successfully.",
        )

    except Exception as e:
        utils.logger.error(f"Error in check_account_credits: {e}")
        return ResponseParser.getParsedErrorMessage(f"Error checking credits: {str(e)}")

