
#!/usr/bin/env python3
"""
Backup manager for critical bot data
"""

import asyncio
import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from notifier import send_alert

class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 10
        
    async def create_backup(self):
        """Create timestamped backup of critical files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = self.backup_dir / f"backup_{timestamp}"
            backup_folder.mkdir(exist_ok=True)
            
            # Files to backup
            critical_files = [
                "file_index.json",
                "main.py",
                "requirements.txt",
                ".replit"
            ]
            
            backed_up = []
            for file in critical_files:
                if Path(file).exists():
                    shutil.copy2(file, backup_folder / file)
                    backed_up.append(file)
            
            # Backup sessions directory
            if Path("sessions").exists():
                shutil.copytree("sessions", backup_folder / "sessions")
                backed_up.append("sessions/")
            
            # Create backup info
            backup_info = {
                "timestamp": timestamp,
                "files": backed_up,
                "size_mb": sum(f.stat().st_size for f in backup_folder.rglob("*") if f.is_file()) / 1024 / 1024
            }
            
            with open(backup_folder / "backup_info.json", 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            await self.cleanup_old_backups()
            
            print(f"✅ Backup created: {timestamp} ({backup_info['size_mb']:.1f} MB)")
            return True
            
        except Exception as e:
            await send_alert(f"❌ Backup failed: {e}")
            return False
    
    async def cleanup_old_backups(self):
        """Remove old backups beyond the limit"""
        try:
            backups = sorted([d for d in self.backup_dir.iterdir() if d.is_dir()])
            
            while len(backups) > self.max_backups:
                oldest = backups.pop(0)
                shutil.rmtree(oldest)
                print(f"🗑️ Removed old backup: {oldest.name}")
                
        except Exception as e:
            print(f"Warning: Backup cleanup failed: {e}")
    
    async def restore_from_backup(self, backup_name: str):
        """Restore from a specific backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup {backup_name} not found")
        
        try:
            # Read backup info
            with open(backup_path / "backup_info.json", 'r') as f:
                backup_info = json.load(f)
            
            # Restore files
            for file in backup_info["files"]:
                source = backup_path / file
                if source.exists():
                    if source.is_dir():
                        if Path(file).exists():
                            shutil.rmtree(file)
                        shutil.copytree(source, file)
                    else:
                        shutil.copy2(source, file)
            
            await send_alert(f"✅ Restored from backup: {backup_name}")
            return True
            
        except Exception as e:
            await send_alert(f"❌ Restore failed: {e}")
            return False

if __name__ == "__main__":
    async def main():
        manager = BackupManager()
        
        # Create backup every 6 hours
        while True:
            await manager.create_backup()
            await asyncio.sleep(6 * 3600)  # 6 hours
    
    asyncio.run(main())
