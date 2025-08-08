
#!/usr/bin/env python3
"""
Simple web dashboard for monitoring bot supervisor status
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify
import psutil

app = Flask(__name__)

def get_bot_status():
    """Get status of all bot processes"""
    bots = ['index_bot.py', 'file_forwarder_sc.py', 'forward_clean_bot.py']
    status = {}
    
    for bot in bots:
        status[bot] = {
            'running': False,
            'pid': None,
            'memory_usage': 0,
            'cpu_percent': 0
        }
        
        # Check if process is running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and any(bot in cmd for cmd in proc.info['cmdline']):
                    status[bot]['running'] = True
                    status[bot]['pid'] = proc.info['pid']
                    status[bot]['memory_usage'] = proc.memory_info().rss / 1024 / 1024  # MB
                    status[bot]['cpu_percent'] = proc.cpu_percent()
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    return status

def get_system_info():
    """Get system resource information"""
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    }

def get_file_index_stats():
    """Get statistics about the file index"""
    try:
        with open('file_index.json', 'r') as f:
            index = json.load(f)
            return {
                'total_files': len(index),
                'last_updated': datetime.fromtimestamp(os.path.getmtime('file_index.json')).strftime('%Y-%m-%d %H:%M:%S')
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return {'total_files': 0, 'last_updated': 'Never'}

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API endpoint for real-time status"""
    return jsonify({
        'bots': get_bot_status(),
        'system': get_system_info(),
        'index': get_file_index_stats(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/restart/<bot_name>')
def restart_bot(bot_name):
    """Restart a specific bot (kills process, supervisor will restart it)"""
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
