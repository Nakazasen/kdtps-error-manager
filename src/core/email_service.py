"""
Email Service for KDTPS Error Manager
Gửi email thông báo cho người phụ trách.
"""
import smtplib
import logging
from email.message import EmailMessage
from typing import Optional, List
from utils.config import config

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications using SMTP."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = EmailService()
        return cls._instance
        
    def __init__(self):
        # Default settings - normally these should be in a separate SMTP config
        # but using AppConfig values where available.
        self.smtp_server = "localhost" # Default internal SMTP
        self.smtp_port = 25
        self.sender_email = "kdtps-noreply@dtvn.kyocera.com"
        
    def send_notification(self, recipient: str, subject: str, body: str, is_html: bool = False) -> bool:
        """
        Send an email notification.
        
        Args:
            recipient: Email address of the recipient.
            subject: Subject line.
            body: Message content.
            is_html: Whether the body is HTML.
            
        Returns:
            True if successful, False otherwise.
        """
        if not recipient:
            logger.warning("Email: No recipient specified.")
            return False
            
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = recipient
        
        if is_html:
            msg.set_content("Please enable HTML to view this message.")
            msg.add_alternative(body, subtype='html')
        else:
            msg.set_content(body)
            
        try:
            logger.info(f"Email: Attempting to send to {recipient}...")
            # Use fixed timeout for server attempts
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.send_message(msg)
            logger.info(f"Email: Successfully sent to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Email: Failed to send to {recipient}: {e}")
            return False

    def format_error_notification(self, record: dict) -> str:
        """Format a basic text notification for a new error."""
        no_dvd = record.get('no_dvd', 'N/A')
        machine = record.get('col_c', 'N/A')
        line = record.get('col_d', 'N/A')
        code = record.get('col_g', record.get('col_h', 'N/A'))
        
        body = (
            f"Thông báo lỗi KDTPS mới\n"
            f"---------------------------\n"
            f"Số điểm vấn đề: {no_dvd}\n"
            f"Loại máy: {machine}\n"
            f"Line: {line}\n"
            f"Mã lỗi: {code}\n"
            f"---------------------------\n"
            f"Vui lòng vào phần mềm KDTPS Error Manager để cập nhật nội dung điều tra.\n"
            f"(Đây là email tự động, vui lòng không trả lời)"
        )
        return body
