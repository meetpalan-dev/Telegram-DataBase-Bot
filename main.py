#!/usr/bin/env python3
"""
Advanced Supervisor for Telegram Bots
- Concurrent bot management with crash protection
- Telegram alerts for failures
- Resource monitoring
- Integrated web dashboard
- Replit keep_alive support
"""

import asyncio
import logging
import signal
import os
import json
from pathlib import Path
from typing import List
from datetime import datetime
from threading import Thread
import psutil
from flask import Flask, render_template, jsonify

from notifier import send_alert

# --- Flask dashboard app ---
dashboard_app = Flask(__name__)

@dashboard_app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@dashboard_app.route('/ping')
def ping():
    """Health check route for UptimeRobot"""
    return "✅ Supervisor is alive!"

@dashboard_app.route('/api/status')
def api_status():
    """API endpoint for real-time status"""
    return jsonify({
        'bots': get_bot_status(),
        'system': get_system_info(),
        'index': get_file_index_stats(),
        'timestamp': datetime.now().isoformat()
    })

@dashboard_app.route('/api/restart/<bot_name>')
def restart_bot(bot_name):
    valid_bots = ['index_bot.py', 'file_forwarder_sc.py', 'forward_clean_bot.py']
    if bot_name not in valid_bots:
        return jsonify({'error': 'Invalid bot name'}), 400

    killed = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any(bot_name in cmd for cmd in proc.info['cmdline']):
                proc.terminate()
                killed = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return jsonify({
        'success': killed,
        'message': f'{"Restart signal sent to" if killed else "No running process found for"} {bot_name}'
    })

def run_dashboard():
    dashboard_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_dashboard)
    t.daemon = True
    t.start()

keep_alive()

# --- Logging configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_supervisor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# --- Utility Functions ---
def get_bot_status():
    bots = ['index_bot.py', 'file_forwarder_sc.py', 'forward_clean_bot.py']
    status = {}

    for bot in bots:
        status[bot] = {
            'running': False,
            'pid': None,
            'memory_usage': 0,
            'cpu_percent': 0
        }
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and any(bot in cmd for cmd in proc.info['cmdline']):
                    status[bot]['running'] = True
                    status[bot]['pid'] = proc.info['pid']
                    status[bot]['memory_usage'] = proc.memory_info().rss / 1024 / 1024
                    status[bot]['cpu_percent'] = proc.cpu_percent()
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return status

def get_system_info():
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    }

def get_file_index_stats():
    try:
        with open('file_index.json', 'r') as f:
            index = json.load(f)
            return {
                'total_files': len(index),
                'last_updated': datetime.fromtimestamp(os.path.getmtime('file_index.json')).strftime('%Y-%m-%d %H:%M:%S')
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return {'total_files': 0, 'last_updated': 'Never'}

# --- Bot Supervisor Class ---
class BotSupervisor:
    def __init__(self, scripts: List[str]):
        self.scripts = scripts
        self.processes: List[asyncio.subprocess.Process] = []
        self.shutdown_signal = asyncio.Event()
        self.max_restarts = 5
        self.restart_counts = {script: 0 for script in scripts}

    async def resource_check(self) -> bool:
        try:
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                logger.warning("⚠️ High memory usage: %s%%", mem.percent)
                return False
            return True
        except Exception as e:
            logger.error("Resource check failed: %s", e)
            return True

    async def run_script(self, script: str, delay: float = 0) -> None:
        await asyncio.sleep(delay)
        script_path = Path(script)
        if not script_path.exists():
            msg = f"❌ Script not found: {script}"
            logger.error(msg)
            await send_alert(msg)
            return

        while not self.shutdown_signal.is_set():
            if not await self.resource_check():
                await asyncio.sleep(10)
                continue

            try:
                logger.info("Launching %s (attempt %d/%d)", 
                            script, self.restart_counts[script] + 1, self.max_restarts)

                proc = await asyncio.create_subprocess_exec(
                    "python", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=1024 * 256,
                    env=os.environ.copy()
                )
                self.processes.append(proc)

                async def read_stream(stream, prefix):
                    while not self.shutdown_signal.is_set():
                        line = await stream.readline()
                        if not line:
                            break
                        logger.info("[%s] %s", prefix, line.decode().strip())

                readers = [
                    asyncio.create_task(read_stream(proc.stdout, script)),
                    asyncio.create_task(read_stream(proc.stderr, f"{script}-stderr"))
                ]

                await proc.wait()
                for task in readers:
                    task.cancel()

                if proc.returncode != 0:
                    msg = f"❌ `{script}` crashed with exit code {proc.returncode}"
                    logger.warning(msg)
                    await send_alert(msg)
                    self.restart_counts[script] += 1

                    if self.restart_counts[script] >= self.max_restarts:
                        final_msg = f"🚨 Max restarts reached for `{script}`. Stopping further attempts."
                        logger.error(final_msg)
                        await send_alert(final_msg)
                        break

                    if proc.returncode == 1:
                        await asyncio.sleep(3600)
                    else:
                        await asyncio.sleep(30)
                else:
                    self.restart_counts[script] = 0

            except Exception as e:
                err_msg = f"❗ Error running `{script}`:\n{e}"
                logger.error(err_msg, exc_info=True)
                await send_alert(err_msg)
                await asyncio.sleep(10)

        logger.info("Stopped monitoring %s", script)

    async def run_health_monitor(self, health_monitor):
        while not self.shutdown_signal.is_set():
            try:
                await health_monitor.run_health_check()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error("Health monitor error: %s", e)
                await asyncio.sleep(60)

    async def run_backup_manager(self, backup_manager):
        while not self.shutdown_signal.is_set():
            try:
                await backup_manager.create_backup()
                await asyncio.sleep(6 * 3600)
            except Exception as e:
                logger.error("Backup manager error: %s", e)
                await asyncio.sleep(3600)

    async def shutdown(self) -> None:
        logger.info("Initiating shutdown sequence")
        self.shutdown_signal.set()

        for proc in self.processes:
            if proc.returncode is None:
                try:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        logger.warning("Force killing process %d", proc.pid)
                        proc.kill()
                except ProcessLookupError:
                    pass

    async def monitor(self) -> None:
        startup_delays = [i * 10 for i in range(len(self.scripts))]
        bot_tasks = [
            asyncio.create_task(self.run_script(script, delay))
            for script, delay in zip(self.scripts, startup_delays)
        ]

        from health_monitor import HealthMonitor
        from backup_manager import BackupManager
        health_monitor = HealthMonitor()
        backup_manager = BackupManager()

        all_tasks = bot_tasks + [
            asyncio.create_task(self.run_health_monitor(health_monitor)),
            asyncio.create_task(self.run_backup_manager(backup_manager))
        ]

        try:
            await asyncio.gather(*all_tasks)
        except Exception as e:
            logger.critical("Monitor error: %s", e, exc_info=True)
            await send_alert(f"💥 Fatal monitor crash:\n{e}")
        finally:
            await self.shutdown()

# --- Main Entrypoint ---
async def main():
    required_vars = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_BOT_TOKEN']
    for var in required_vars:
        if var not in os.environ:
            logger.critical("Missing env var: %s", var)
            await send_alert(f"❌ Missing required env var: {var}")
            return

    supervisor = BotSupervisor([
        "index_bot.py",
        "file_forwarder_sc.py",
        "forward_clean_bot.py"
    ])

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(supervisor.shutdown()))

    try:
        await supervisor.monitor()
    except asyncio.CancelledError:
        logger.info("Shutdown completed")
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        await send_alert(f"🔥 Supervisor fatal error:\n{e}")
    finally:
        logger.info("Supervisor stopped")

if __name__ == "__main__":
    try:
        Path("sessions").mkdir(exist_ok=True)
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.critical("Initialization failed: %s", e)
