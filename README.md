# Telegram Database Bot System

A Telegram-based file storage and retrieval system that turns a channel into a searchable database.

Instead of hosting files on a traditional server, this project uses Telegram as the storage layer.  
Files are uploaded, filtered, forwarded to an authorized storage channel, indexed automatically, and later retrieved through keyword search.

The system behaves more like a small backend service than a simple bot — handling ingestion, indexing, querying and monitoring as separate responsibilities.

---

## How It Works

### Write Flow (File Ingestion)

User Upload  
→ Bot receives file  
→ File is filtered and forwarded to authorized channel  
→ Channel mirrors to group  
→ Index bot scans messages and stores metadata

The channel acts as the database while `file_index.json` acts as the searchable table.

---

### Read Flow (File Retrieval)

User types keyword in group  
→ Bot searches indexed metadata  
→ Matching message IDs found  
→ Files copied from storage channel  
→ Results delivered in batches

Users never need exact filenames — partial keywords work.

---

## Components

**Worker Bots**
- `file_forwarder_sc.py` — filters and forwards uploaded files
- `index_bot.py` — scans channel and builds searchable index
- `forward_clean_bot.py` — manages forwarded messages

**Supervisor & Services**
- Supervisor — keeps bots running
- Health monitor — checks runtime status
- Backup manager — preserves index data
- Web dashboard — shows server status

---

## Features

- Telegram channel used as storage backend
- Automatic file ingestion pipeline
- Keyword search (filename + caption)
- Indexed retrieval system
- Paginated results ("see more")
- Multi-process architecture
- Service monitoring dashboard
- Automatic restart supervision

---

## Project Structure

bot/            worker bots  
core/           indexing logic  
services/       background services  
supervisor/     process manager  
panel/          dashboard routes  
templates/      UI pages  

---

## Setup

1. Install dependencies
pip install -r requirements.txt

2. Create environment config
Copy `.env.example` → `.env`

3. Run the supervisor
python -m supervisor.main

---

## Purpose

This project was built to explore system design concepts using unconventional infrastructure — using a messaging platform as a storage backend while maintaining searchable access and service reliability.
