path = r'c:\ProgramData\Sandbox\kdtps-error-manager\src\ui\settings_dialog.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'config.save_to_file()' in line:
        # Add refresh call
        lines.insert(i + 1, '            \n            # Refresh Auto-sync (Phase 7)\n            try:\n                from core.sync_manager import SyncManager\n                SyncManager.get_instance().update_config()\n            except Exception as e:\n                logger.error(f"Failed to refresh SyncManager: {e}")\n')
        break

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patch applied: SettingsDialog now refreshes SyncManager.")
