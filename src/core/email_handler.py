"""
Email Handler for KDTPS Error Manager
Outlook integration via win32com for sending KDTPS reply emails.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class EmailHandler:
    """Handles email operations via Outlook."""
    
    def __init__(self):
        self._outlook = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Outlook."""
        return self._connected
    
    def connect(self) -> bool:
        """Connect to Outlook via COM."""
        try:
            import win32com.client
            
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            self._connected = True
            logger.info("Connected to Outlook")
            return True
            
        except ImportError:
            logger.error("pywin32 not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Outlook: {e}")
            return False
    
    def create_kdtps_reply(
        self,
        record: Dict[str, Any],
        to_emails: List[str] = None,
        cc_emails: List[str] = None,
        attachment_path: str = None
    ) -> bool:
        """
        Create and display KDTPS reply email.
        
        Args:
            record: Error record data
            to_emails: List of recipient emails
            cc_emails: List of CC emails
            attachment_path: Path to reply Excel file
        
        Returns:
            True if email created successfully
        """
        if not self._connected:
            if not self.connect():
                return False
        
        try:
            from utils.config import config
            
            # Default recipients
            if not to_emails:
                to_emails = config.kdtps_email_to
            
            # Create mail item
            logger.debug("Creating Outlook mail item...")
            mail = self._outlook.CreateItem(0)  # 0 = Mail item
            
            # Set recipients
            logger.debug(f"Setting recipients: {to_emails}")
            mail.To = "; ".join(to_emails)
            if cc_emails:
                mail.CC = "; ".join(cc_emails)
            
            # Build subject
            no_dvd = record.get('no_dvd', '')
            machine_type = record.get('col_c', '')
            subject = f"【KDTPS】不具合状況連絡 No.{no_dvd} - {machine_type}"
            mail.Subject = subject
            
            # Build body
            logger.debug("Building email body...")
            body = self._build_email_body(record)
            mail.HTMLBody = body
            
            # Add attachment if provided
            if attachment_path and Path(attachment_path).exists():
                logger.info(f"Adding attachment: {attachment_path}")
                mail.Attachments.Add(str(Path(attachment_path).resolve()))
                logger.debug("Attachment added")
            
            # Display email (don't send automatically)
            logger.info("Displaying Outlook email window...")
            mail.Display()
            
            logger.info(f"Created KDTPS reply email for No.{no_dvd}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create email: {e}")
            return False
    
    def _build_email_body(self, record: Dict[str, Any]) -> str:
        """Build HTML email body from record data."""
        no_dvd = record.get('no_dvd', '')
        machine_type = record.get('col_c', '')
        line = record.get('col_d', '')
        error_code_g = record.get('col_g', '')
        error_code_h = record.get('col_h', '')
        error_content_jp = record.get('col_j', '')
        investigation = record.get('col_n', '')
        
        # HTML template
        html = f"""
<html>
<head>
<style>
    body {{ font-family: "Meiryo", "Yu Gothic", sans-serif; font-size: 11pt; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background-color: #4472C4; color: white; }}
    .header {{ color: #1976D2; font-weight: bold; }}
    .section {{ margin: 15px 0; }}
</style>
</head>
<body>

<p>お疲れ様です。</p>
<p>下記の不具合について、調査結果をご連絡いたします。</p>

<div class="section">
<p class="header">■ 不具合情報</p>
<table>
    <tr><th>No.</th><td>{no_dvd}</td></tr>
    <tr><th>機種</th><td>{machine_type}</td></tr>
    <tr><th>Line</th><td>{line}</td></tr>
    <tr><th>エラーコード</th><td>{error_code_g} {error_code_h}</td></tr>
    <tr><th>不具合内容</th><td>{error_content_jp}</td></tr>
</table>
</div>

<div class="section">
<p class="header">■ 調査結果 / Investigation Result</p>
<table>
    <tr><td style="white-space: pre-wrap;">{investigation}</td></tr>
</table>
</div>

<p>何かご不明点がありましたら、ご連絡ください。</p>
<p>よろしくお願いいたします。</p>

<hr>
<p style="color: #666; font-size: 9pt;">
※ このメールはKDTPS Error Managerから自動生成されました。
</p>

</body>
</html>
"""
        return html
    
    def send_notification(
        self,
        handler_email: str,
        record: Dict[str, Any],
        message: str = None
    ) -> bool:
        """
        Send notification email to assigned handler.
        
        Args:
            handler_email: Email address of handler
            record: Error record data
            message: Optional custom message
        
        Returns:
            True if sent successfully
        """
        if not self._connected:
            if not self.connect():
                return False
        
        if not handler_email:
            logger.warning("No handler email provided")
            return False
        
        try:
            mail = self._outlook.CreateItem(0)
            
            mail.To = handler_email
            
            no_dvd = record.get('no_dvd', '')
            machine_type = record.get('col_c', '')
            mail.Subject = f"[割当] KDTPS No.{no_dvd} - {machine_type}"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
            <p>Chào anh/chị,</p>
            <p>Bạn được giao nhiệm vụ điều tra lỗi KDTPS sau:</p>
            <ul>
                <li><strong>No:</strong> {no_dvd}</li>
                <li><strong>Loại máy:</strong> {machine_type}</li>
                <li><strong>Line:</strong> {record.get('col_d', '')}</li>
            </ul>
            {f'<p><em>{message}</em></p>' if message else ''}
            <p>Vui lòng cập nhật tiến độ trong hệ thống KDTPS Error Manager.</p>
            <hr>
            <p style="color: #666; font-size: 9pt;">
            Email tự động từ KDTPS Error Manager
            </p>
            </body>
            </html>
            """
            mail.HTMLBody = body
            
            mail.Display()  # Show for review before sending
            
            logger.info(f"Notification email created for {handler_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def create_aggr_notification(
        self,
        handler_email: str,
        handler_name: str,
        records: List[Dict[str, Any]]
    ) -> bool:
        """
        Create summary email for multiple records.
        """
        if not self._connected:
            if not self.connect():
                return False
        
        if not handler_email:
            return False
            
        try:
            mail = self._outlook.CreateItem(0)
            mail.To = handler_email
            
            count = len(records)
            mail.Subject = f"[KDTPS] Tổng hợp {count} điếm vấn đề cần xử lý - {handler_name}"
            
            # Build Table Rows
            rows_html = ""
            for r in records:
                no_dvd = r.get('no_dvd', '')
                machine = r.get('col_c', '')
                line = r.get('col_d', '')  # Was incorrectly using col_a
                content = r.get('col_l', '') # Was incorrectly using col_j
                if len(content) > 120:
                    content = content[:120] + "..."
                
                rows_html += f"""
                <tr>
                    <td>{no_dvd}</td>
                    <td>{machine}</td>
                    <td>{line}</td>
                    <td>{content}</td>
                </tr>
                """
            
            body = f"""
            <html>
            <head>
            <style>
                body {{ font-family: "Meiryo", "Yu Gothic", sans-serif; font-size: 11pt; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
                th {{ background-color: #4472C4; color: white; }}
            </style>
            </head>
            <body>
            <p>Chào {handler_name},</p>
            <p>Hệ thống KDTPS Error Manager xin gửi tổng hợp <strong>{count}</strong> điểm vấn đề đang chờ anh/chị xử lý:</p>
            
            <table>
                <tr>
                    <th width="10%">No.</th>
                    <th width="15%">Loại máy</th>
                    <th width="10%">Line</th>
                    <th>Nội dung lỗi</th>
                </tr>
                {rows_html}
            </table>
            
            <p>Vui lòng kiểm tra và cập nhật tiến độ trên hệ thống.</p>
            <hr>
            <p style="color: #666; font-size: 9pt;">
            Email tự động từ KDTPS Error Manager
            </p>
            </body>
            </html>
            """
            
            mail.HTMLBody = body
            mail.Display()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create aggregate email: {e}")
            return False


# Singleton instance
_handler_instance: Optional[EmailHandler] = None

def get_email_handler() -> EmailHandler:
    """Get or create EmailHandler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = EmailHandler()
    return _handler_instance
