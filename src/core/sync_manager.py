import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
from utils.config import config
from core.database import get_database

logger = logging.getLogger(__name__)

class SyncWorker(QThread):
    """Worker thread for non-blocking network scanning (Phase 7.2)."""
    sync_completed = pyqtSignal(dict) # {dept_name: new_records_count}
    error_occurred = pyqtSignal(str)

    def __init__(self, last_sync_data: dict):
        super().__init__()
        self.last_sync_data = last_sync_data
        self.new_sync_data = last_sync_data.copy()
        self.start_time = datetime.now()
        self.end_time = None
        self.status = "Success"
        self.message = ""

    def run(self):
        try:
            db = get_database()
            depts = db.get_departments()
            results = {}
            
            from core.excel_handler import ExcelHandler
            excel = ExcelHandler()
            
            for dept in depts:
                dept_name = dept['name']
                network_path = dept['network_path']
                
                if not network_path or not os.path.exists(network_path):
                    continue
                
                # Find files
                files = list(Path(network_path).glob("File tổng hợp*.xls*"))
                if not files:
                    continue
                
                # Sort by mtime descending
                files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_file = files[0]
                mtime = latest_file.stat().st_mtime
                
                # Skip if already processed
                last_info = self.last_sync_data.get(dept_name, {})
                if last_info.get('file') == str(latest_file) and last_info.get('mtime') == mtime:
                    logger.debug(f"Sync: No change for {dept_name}")
                    continue
                
                logger.info(f"Sync: Processing new file for {dept_name}: {latest_file.name}")
                
                try:
                    stats = excel.import_from_summary(str(latest_file), dept['id'])
                    new_count = stats.get('inserted', 0)
                    
                    if new_count > 0 or stats.get('updated', 0) > 0:
                        results[dept_name] = new_count
                    
                    # Store current state
                    self.new_sync_data[dept_name] = {
                        'file': str(latest_file),
                        'mtime': mtime,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"Sync: Failed to import {dept_name}: {e}")
            
            self.end_time = datetime.now()
            if not results:
                self.status = "Warning"
                self.message = "No new data found"
            else:
                self.status = "Success"
                self.message = f"Found {sum(results.values())} new records"
                
            self.sync_completed.emit(results)
            
        except Exception as e:
            self.end_time = datetime.now()
            self.status = "Error"
            self.message = str(e)
            logger.error(f"Sync Worker Error: {e}")
            self.error_occurred.emit(str(e))

class SyncManager(QObject):
    """Manager for periodic background synchronization (Phase 7.2)."""
    
    _instance = None
    data_synced = pyqtSignal(dict) # {dept_name: count}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SyncManager()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.perform_sync)
        self.worker = None
        
        self.sync_history_path = config.data_dir / "sync_history.json"
        self.last_sync_data = self._load_history()
        
        # Initial config
        self.update_config()
        
    def _load_history(self) -> dict:
        if self.sync_history_path.exists():
            try:
                with open(self.sync_history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_history(self, data: dict):
        try:
            with open(self.sync_history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync history: {e}")

    def update_config(self):
        """Update timer settings from global config."""
        if config.sync_enabled:
            interval_ms = config.sync_interval * 60 * 1000
            self.timer.start(interval_ms)
            logger.info(f"Sync Manager started. Interval: {config.sync_interval} min")
        else:
            self.timer.stop()
            logger.info("Sync Manager stopped.")
            
    def perform_sync(self):
        """Triggers the background sync worker."""
        if self.worker and self.worker.isRunning():
            logger.debug("Sync: Previous worker still running, skipping...")
            return
            
        logger.info("Sync: Starting background update...")
        self.worker = SyncWorker(self.last_sync_data)
        self.worker.sync_completed.connect(self.on_sync_finished)
        self.worker.error_occurred.connect(lambda e: logger.error(f"Sync error: {e}"))
        self.worker.start()
        
    def on_sync_finished(self, results):
        if self.worker:
            self.last_sync_data = self.worker.new_sync_data
            self._save_history(self.last_sync_data)
            
            # Record to database
            try:
                db = get_database()
                db.add_sync_log(
                    start_time=self.worker.start_time,
                    end_time=self.worker.end_time,
                    status=self.worker.status,
                    results=results or {},
                    message=self.worker.message
                )
                self._process_auto_notifications(self.worker.start_time)
                
            except Exception as e:
                logger.error(f"Failed to record sync log: {e}")
                
        if results:
            logger.info(f"Sync finished: {results}")
            self.data_synced.emit(results)
        else:
            logger.debug("Sync finished: No new data.")

    def _process_auto_notifications(self, start_time: datetime):
        """Process automatic email notifications for new records."""
        try:
            from core.database import get_database
            from core.email_service import EmailService
            
            db = get_database()
            new_records = db.get_new_records_to_notify(start_time)
            
            if not new_records:
                return
                
            logger.info(f"Auto-Email: Found {len(new_records)} potential records to notify.")
            email_service = EmailService.get_instance()
            
            for record in new_records:
                no_dvd = record.get('no_dvd')
                recipient = record.get('handler_email')
                
                # Double check to avoid spam
                if db.has_email_been_sent(no_dvd, recipient):
                    logger.debug(f"Auto-Email: Already sent for {no_dvd} to {recipient}")
                    continue
                    
                subject = f"【KDTPS】Thông báo lỗi mới - {no_dvd}"
                body = email_service.format_error_notification(record)
                
                success = email_service.send_notification(recipient, subject, body)
                
                if success:
                    db.log_email_sent(no_dvd, recipient, "Sent")
                    logger.info(f"Auto-Email: Notification sent for {no_dvd} to {recipient}")
                else:
                    db.log_email_sent(no_dvd, recipient, "Failed", "SMTP Error")
                    
        except Exception as e:
            logger.error(f"Auto-Email: Failed to process notifications: {e}")
