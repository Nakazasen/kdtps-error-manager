path = r'c:\ProgramData\Sandbox\kdtps-error-manager\src\ui\settings_dialog.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Update imports
for i, line in enumerate(lines):
    if 'QProgressDialog' in line and ')' in lines[i+1]:
        lines[i] = line.replace('QProgressDialog', 'QProgressDialog,\n    QCheckBox, QSpinBox')
        break

# 2. Add setup_sync_tab call
for i, line in enumerate(lines):
    if 'self.setup_email_tab()' in line:
        lines.insert(i + 1, '        self.setup_sync_tab()\n')
        break

# 3. Add setup_sync_tab method
new_method = """
    def setup_sync_tab(self):
        \"\"\"Setup Sync settings tab (Phase 7.1).\"\"\"
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Cấu hình Tự động Đồng bộ")
        form = QFormLayout(group)
        
        self.chk_sync_enabled = QCheckBox("Bật tự động quét file server (Network Path)")
        form.addRow(self.chk_sync_enabled)
        
        self.spin_sync_interval = QSpinBox()
        self.spin_sync_interval.setRange(5, 120)
        self.spin_sync_interval.setSuffix(" phút")
        form.addRow("Khoảng thời gian quét:", self.spin_sync_interval)
        
        layout.addWidget(group)
        
        lbl_info = QLabel(
            "ℹ️ Khi bật tính năng này, ứng dụng sẽ định kỳ kiểm tra các file Excel\\n"
            "tổng hợp trên server và tự động nạp dữ liệu mới nếu có."
        )
        lbl_info.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(lbl_info)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🔄 Đồng bộ")
"""

for i, line in enumerate(lines):
    if 'self.tabs.addTab(tab, "📧 Email")' in line:
        # Search for the end of the method
        lines.insert(i + 1, new_method + '\n')
        break

# 4. Update load_settings
for i, line in enumerate(lines):
    if 'self.list_emails.addItem(email)' in line:
        # Find the end of for loop
        lines.insert(i + 1, '\n        # Sync (Phase 7.1)\n        self.chk_sync_enabled.setChecked(config.sync_enabled)\n        self.spin_sync_interval.setValue(config.sync_interval)\n')
        break

# 5. Update save_settings
for i, line in enumerate(lines):
    if 'config.email_subject = self.txt_email_subject.text()' in line:
        lines.insert(i + 1, '            # Sync (Phase 7.1)\n            config.sync_enabled = self.chk_sync_enabled.isChecked()\n            config.sync_interval = self.spin_sync_interval.value()\n')
        break

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patch applied to settings_dialog.py")
