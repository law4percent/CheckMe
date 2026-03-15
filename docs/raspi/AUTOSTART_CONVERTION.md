# CheckMe — Autostart on Boot

> **systemd Service Setup Guide**
> Raspberry Pi · User: `checkme` · Project: `/home/checkme/CheckMe/raspi_code`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Create the Service File](#3-create-the-service-file)
4. [Enable and Start](#4-enable-and-start)
5. [Verify It Works](#5-verify-it-works)
6. [Managing the Service](#6-managing-the-service)
7. [Viewing Logs](#7-viewing-logs)
8. [Disabling Auto-Run](#8-disabling-auto-run)
9. [Troubleshooting](#9-troubleshooting)
10. [Quick Reference](#10-quick-reference)

---

## 1. Overview

By default, CheckMe must be started manually with `python main.py` each time
the Pi boots. This guide converts CheckMe into a **systemd service** so it:

- Starts automatically on every boot
- Restarts automatically if `main.py` crashes
- Logs all output viewable with `journalctl`
- Responds to standard `systemctl` commands

---

## 2. Prerequisites

Confirm all of the following before continuing. Auto-run cannot fix
configuration or dependency problems — it will silently fail on every boot
instead.

```bash
# 1. Confirm main.py runs without errors
cd /home/checkme/CheckMe/raspi_code
source /home/checkme/checkme-env/bin/activate
python main.py

# 2. Confirm the venv Python path
which python
# Expected: /home/checkme/checkme-env/bin/python

# 3. Confirm main.py exists at the project path
ls /home/checkme/CheckMe/raspi_code/main.py
```

> ⚠️ **Do not proceed until `python main.py` works correctly from the
> terminal.** Auto-run cannot fix configuration or dependency problems.

---

## 3. Create the Service File

Open a new service file with nano:

```bash
sudo nano /etc/systemd/system/checkme.service
```

Paste the following content exactly:

```ini
[Unit]
Description=CheckMe Grading System
After=network.target local-fs.target

[Service]
Type=simple
User=checkme
WorkingDirectory=/home/checkme/CheckMe/raspi_code
ExecStart=/home/checkme/checkme-env/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
TimeoutStopSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Save and exit: `Ctrl+O` → `Enter` → `Ctrl+X`

> ℹ️ `WorkingDirectory` must point to the project root. CheckMe loads
> `config/.env` and other files using relative paths, so this must be correct.

> ℹ️ `RestartSec=10` gives GPIO and I2C time to settle before a restart after
> a crash.

> ℹ️ `TimeoutStopSec=10` gives `main.py` up to 10 seconds to run
> `GPIO.cleanup()` before systemd force-kills the process.

---

## 4. Enable and Start

Run these commands in order:

```bash
# Reload systemd to pick up the new file
sudo systemctl daemon-reload

# Enable — marks the service to start on every boot
sudo systemctl enable checkme

# Start immediately without rebooting
sudo systemctl start checkme

# Confirm it is active
sudo systemctl status checkme
```

You should see `Active: active (running)` in the status output:

```
● checkme.service - CheckMe Grading System
     Loaded: loaded (/etc/systemd/system/checkme.service; enabled)
     Active: active (running) since ...
   Main PID: 1234 (python)
```

If you see `Active: failed` or `Active: activating`, jump to
[Section 9 — Troubleshooting](#9-troubleshooting).

---

## 5. Verify It Works

```bash
# Confirm main.py is running as a process
ps aux | grep main.py

# Watch live log output for the first 30 seconds
sudo journalctl -u checkme -f --lines=50

# Full reboot test
sudo reboot

# After reboot, SSH back in and confirm:
sudo systemctl status checkme
```

---

## 6. Managing the Service

| Command | Description |
|---|---|
| `sudo systemctl start checkme` | Start the service |
| `sudo systemctl stop checkme` | Stop the service |
| `sudo systemctl restart checkme` | Restart (apply code changes) |
| `sudo systemctl status checkme` | Check current status |
| `sudo systemctl enable checkme` | Enable autostart on boot |
| `sudo systemctl disable checkme` | Disable autostart on boot |

> ⚠️ **Always use `systemctl stop/restart`.** Never use `sudo kill` or
> `sudo pkill python` directly — this bypasses `GPIO.cleanup()` and can
> leave pins in a bad state on the next boot.

---

## 7. Viewing Logs

### systemd journal (boot messages, crashes, restart events)

```bash
# Follow live output
sudo journalctl -u checkme -f

# All output since last boot
sudo journalctl -u checkme -b

# Last 100 lines
sudo journalctl -u checkme -n 100

# Previous boot
sudo journalctl -u checkme -b -1
```

### Application logs (CheckMe logger)

```bash
tail -50  /home/checkme/CheckMe/raspi_code/logs/error.log
tail -50  /home/checkme/CheckMe/raspi_code/logs/warning.log
tail -100 /home/checkme/CheckMe/raspi_code/logs/all.log
tail -f   /home/checkme/CheckMe/raspi_code/logs/all.log
```

---

## 8. Disabling Auto-Run

To return to manual mode (e.g. during development):

```bash
sudo systemctl stop checkme
sudo systemctl disable checkme

# Then run manually as usual:
cd /home/checkme/CheckMe/raspi_code
source /home/checkme/checkme-env/bin/activate
python main.py
```

To re-enable later:

```bash
sudo systemctl enable checkme
sudo systemctl start checkme
```

To fully remove the service file:

```bash
sudo systemctl stop checkme
sudo systemctl disable checkme
sudo rm /etc/systemd/system/checkme.service
sudo systemctl daemon-reload
```

---

## 9. Troubleshooting

Always check the journal first when the service fails:

```bash
sudo journalctl -u checkme -n 50 --no-pager
```

### Common errors

| Symptom in journal | Cause | Fix |
|---|---|---|
| `No such file or directory: main.py` | Wrong `WorkingDirectory` or `ExecStart` path | Check both paths in the service file match your actual install |
| `ModuleNotFoundError: No module named X` | Package missing from venv | Run `/home/checkme/checkme-env/bin/pip install <package>` |
| `FileNotFoundError: config/.env` | Wrong `WorkingDirectory` | `WorkingDirectory` must be the project root, not a subdirectory |
| `PermissionError: /dev/i2c-1` | I2C not enabled or wrong group | `sudo raspi-config` → Interface Options → I2C → Enable |
| `RuntimeError: GPIO channel already in use` | Orphan python process still running | `ps aux | grep python` then `sudo kill <PID>` |
| Service restarts in a loop | Crash on startup | Read the journal error and fix the root cause before restarting |

### GPIO / I2C permission denied

```bash
sudo usermod -aG gpio,i2c checkme
sudo reboot
```

### LCD blank after autostart

The service may be starting before hardware is ready. Increase the delay:

```bash
# Edit the service file and change RestartSec=10 to RestartSec=15
sudo nano /etc/systemd/system/checkme.service

sudo systemctl daemon-reload
sudo systemctl restart checkme
```

### Packages installed but service can't find them

```bash
# Confirm the venv python can see the package
/home/checkme/checkme-env/bin/python -c "import RPi.GPIO; print('OK')"

# If it fails, install into the venv directly
/home/checkme/checkme-env/bin/pip install RPi.GPIO
```

---

## 10. Quick Reference

```bash
# ── Setup ────────────────────────────────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable checkme

# ── Control ──────────────────────────────────────────────────────────────────
sudo systemctl start   checkme
sudo systemctl stop    checkme
sudo systemctl restart checkme
sudo systemctl status  checkme

# ── Logs ─────────────────────────────────────────────────────────────────────
sudo journalctl -u checkme -f
sudo journalctl -u checkme -b
tail -f /home/checkme/CheckMe/raspi_code/logs/all.log

# ── Disable ──────────────────────────────────────────────────────────────────
sudo systemctl stop    checkme
sudo systemctl disable checkme
```