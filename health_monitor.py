
#!/usr/bin/env python3
"""
Health monitoring system for bot supervisor
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any
import psutil
from notifier import send_alert

class HealthMonitor:
    def __init__(self):
        self.health_file = "health_status.json"
        self.last_alert_time = {}
        self.alert_cooldown = 1800  # 30 minutes
        
    async def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        health = {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
            "issues": []
        }
        
        # Check for issues
        if health["cpu_percent"] > 90:
            health["issues"].append("High CPU usage")
            
        if health["memory_percent"] > 90:
            health["issues"].append("High memory usage")
            
        if health["disk_percent"] > 90:
            health["issues"].append("Low disk space")
            
        return health
    
    async def check_file_integrity(self) -> Dict[str, Any]:
        """Check critical files integrity"""
        critical_files = [
            "main.py", "index_bot.py", "file_forwarder_sc.py", 
            "forward_clean_bot.py", "file_index.json"
        ]
        
        integrity = {"missing_files": [], "corrupted_files": []}
        
        for file in critical_files:
            if not Path(file).exists():
                integrity["missing_files"].append(file)
            elif file == "file_index.json":
                try:
                    with open(file, 'r') as f:
                        json.load(f)
                except (json.JSONDecodeError, Exception):
                    integrity["corrupted_files"].append(file)
        
        return integrity
    
    async def send_health_alert(self, message: str, alert_type: str = "health"):
        """Send health alert with cooldown"""
        current_time = time.time()
        last_alert = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_alert > self.alert_cooldown:
            await send_alert(f"🏥 Health Monitor:\n{message}")
            self.last_alert_time[alert_type] = current_time
    
    async def run_health_check(self):
        """Run comprehensive health check"""
        try:
            # System health
            system_health = await self.check_system_health()
            
            # File integrity
            file_integrity = await self.check_file_integrity()
            
            # Save health status
            health_status = {
                "system": system_health,
                "files": file_integrity,
                "last_check": time.time()
            }
            
            with open(self.health_file, 'w') as f:
                json.dump(health_status, f, indent=2)
            
            # Send alerts if needed
            if system_health["issues"]:
                await self.send_health_alert(
                    f"System issues detected:\n" + "\n".join(system_health["issues"]),
                    "system"
                )
            
            if file_integrity["missing_files"]:
                await self.send_health_alert(
                    f"Missing critical files:\n" + "\n".join(file_integrity["missing_files"]),
                    "files"
                )
            
            if file_integrity["corrupted_files"]:
                await self.send_health_alert(
                    f"Corrupted files detected:\n" + "\n".join(file_integrity["corrupted_files"]),
                    "corruption"
                )
                
        except Exception as e:
            await send_alert(f"❌ Health monitor error: {e}")

if __name__ == "__main__":
    async def main():
        monitor = HealthMonitor()
        while True:
            await monitor.run_health_check()
            await asyncio.sleep(300)  # Check every 5 minutes
    
    asyncio.run(main())
