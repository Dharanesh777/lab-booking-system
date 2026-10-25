
import logging
import os
import smtplib
from email.message import EmailMessage

from app.core.config import PERIODS
from app.core.database import users
from app.services.lab_service import get_lab

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM", username).strip()

    if not all([host, username, password, sender, to_email]):
        logger.warning("Email skipped: SMTP configuration is incomplete")
        return False

    try:
        port = int(os.getenv("SMTP_PORT", "587"))

        message = EmailMessage()
        message["From"] = sender
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(username, password)
                server.send_message(message)

        logger.info("Email sent to %s", to_email)
        return True

    except (OSError, ValueError, smtplib.SMTPException):
        logger.exception("Failed to send email to %s", to_email)
        return False


def booking_details(booking: dict) -> str:
    lab_id = str(booking.get("lab_id", "Unknown"))
    lab = get_lab(lab_id)

    periods = "\n".join(
        f"Period {hour}: {PERIODS.get(hour, 'Time unavailable')}"
        for hour in booking.get("hours", [])
    ) or "Not specified"

    return (
        f"Lab: {lab.get('name', lab_id)}\n"
        f"Date: {booking.get('start_date', 'Not specified')}\n"
        f"Periods:\n{periods}\n"
        f"Reason: {booking.get('reason', 'Not specified')}\n"
        f"Booking ID: {booking.get('_id', 'Not specified')}"
    )


def notify_admins_new_booking(booking: dict) -> None:
    if booking.get("type") != "student":
        return

    recipients = [
        user["email"]
        for user in users.find(
            {"role": "admin", "active": {"$ne": False}},
            {"email": 1},
        )
        if user.get("email")
    ]

    fallback = os.getenv("ADMIN_NOTIFICATION_EMAIL", "").strip()
    if fallback:
        recipients.append(fallback)

    student = booking.get("student", {})
    subject = "New lab booking request"
    body = (
        "A student has submitted a lab booking request.\n\n"
        f"Student: {student.get('name', 'Unknown')}\n"
        f"Roll number: {student.get('roll_no', 'Unknown')}\n"
        f"Email: {student.get('email', 'Unknown')}\n"
        f"Status: {booking.get('status', 'pending')}\n\n"
        f"{booking_details(booking)}\n\n"
        "Please sign in to review the request."
    )

    for recipient in dict.fromkeys(recipients):
        send_email(recipient, subject, body)


def notify_student_booking_update(
    booking: dict,
    event: str,
) -> None:
    if booking.get("type") != "student":
        return

    student = booking.get("student", {})
    email = student.get("email")

    messages = {
        "approved": (
            "Lab booking confirmed",
            "Your lab booking has been approved.",
        ),
        "rejected": (
            "Lab booking request rejected",
            "Your lab booking request was rejected.",
        ),
        "cancelled": (
            "Lab booking cancelled",
            "Your lab booking was cancelled by an administrator.",
        ),
    }

    if not email or event not in messages:
        logger.warning("Student notification skipped: missing email or invalid event")
        return

    subject, intro = messages[event]
    note = booking.get("note", "")

    body = (
        f"Hello {student.get('name', 'Student')},\n\n"
        f"{intro}\n\n"
        f"{booking_details(booking)}\n"
        f"Status: {event}\n"
        f"{'Admin note: ' + note + chr(10) if note else ''}\n"
        "Please sign in to the Lab Booking System for details."
    )

    send_email(str(email), subject, body)

def notify_affected_students(bookings_affected):
    for booking in bookings_affected:
        status = booking.get("status")

        if status in {"cancelled", "rejected"}:
            notify_student_booking_update(booking, status)
