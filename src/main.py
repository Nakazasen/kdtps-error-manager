"""
KDTPS Error Manager - Main Entry Point
"""
import sys
import logging
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def setup_logging():
    """Configure application logging with DEBUG level for troubleshooting."""
    from utils.config import get_app_data_dir
    from datetime import datetime
    
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Use DEBUG level for detailed troubleshooting
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_dir / "debug.log", encoding='utf-8', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    # Log session start
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(f"KDTPS Error Manager - Log Session: {datetime.now()}")
    logger.info(f"Log file: {log_dir / 'debug.log'}")
    logger.info("=" * 60)


def main():
    """Application entry point."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting KDTPS Error Manager...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from ui.main_window import MainWindow
        
        # Enable high DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        app = QApplication(sys.argv)
        app.setApplicationName("KDTPS Error Manager")
        app.setOrganizationName("PE Dept")
        app.setOrganizationDomain("kyocera.com")
        
        # Apply dark-ish style
        app.setStyle("Fusion")
        
        # Show Login Dialog (User Selection)
        from ui.login_dialog import LoginDialog
        login = LoginDialog()
        if login.exec() == LoginDialog.DialogCode.Accepted:
            current_user = login.get_user()
            logger.info(f"Login successful for user: {current_user}")
            
            window = MainWindow(current_user=current_user)
            window.show()
            
            logger.info("Application window shown")
            sys.exit(app.exec())
        else:
            logger.info("Login cancelled by user. Exiting.")
            sys.exit(0)
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
