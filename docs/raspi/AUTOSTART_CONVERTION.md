# CheckMe: Autostart on Boot
> How to make CheckMe run automatically when the Raspberry Pi powers on

---

## Table of Contents

- [Overview](#overview)
- [Method: systemd Service](#method-systemd-service)
- [Step 1: Find Your Python Path](#step-1-find-your-python-path)
- [Step 2: Create the Service File](#step-2-create-the-service-file)
- [Step 3: Enable and Start the Service](#step-3-enable-and-start-the-service)
- [Step 4: Verify It Works](#step-4-verify-it-works)
- [Managing the Service](#managing-the-service)
- [Viewing Logs](#viewing-logs)
- [Disabling Autostart](#disabling-autostart)
- [Troubleshooting](#troubleshooting)

---

## Overview

By default, you need to manually run `python main.py` every time the Raspberry Pi boots. This guide converts CheckMe into a **systemd service** so it:

- Starts automatically on every boot
- Restarts automatically if it crashes
- Can be managed with standard `systemctl` commands
- Logs output to the system journal

---

## Step 1: Find Your Python Path

Make sure you know the exact path to your virtual environment's Python binary.

```bash
which python3
# or if using a venv:
source /home/pi/CheckMe/raspi_code/venv/bin/activate
which python
```

Note the full path. It will look something like:
```
/home/pi/CheckMe/raspi_code/venv/bin/python
```

Also confirm your project path:
```bash
ls /home/pi/CheckMe/raspi_code/main.py
# Should return the file path without error
```

---

## Step 2: Create the Service File

Create the systemd service file:

```bash
sudo nano /etc/systemd/system/checkme.service
```

Paste the following — **replace the paths with your actual paths**:

```ini
[Unit]
Description=CheckMe Grading System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/CheckMe/raspi_code
ExecStart=/home/pi/CheckMe/raspi_code/venv/bin/python main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Save and exit: `Ctrl+O` → `Enter` → `Ctrl+X`

> ⚠️ Make sure `WorkingDirectory` and `ExecStart` point to your actual project location and virtual environment. The `WorkingDirectory` must be set correctly because the app loads `config/.env` using relative paths.

---

## Step 3: Enable and Start the Service

Reload systemd to pick up the new service file:
```bash
sudo systemctl daemon-reload
```

Enable the service to run on every boot:
```bash
sudo systemctl enable checkme
```

Start it now without rebooting:
```bash
sudo systemctl start checkme
```

---

## Step 4: Verify It Works

Check the service status:
```bash
sudo systemctl status checkme
```

You should see something like:
```
● checkme.service - CheckMe Grading System
     Loaded: loaded (/etc/systemd/system/checkme.service; enabled)
     Active: active (running) since ...
```

Then reboot and confirm it starts automatically:
```bash
sudo reboot
# After reboot:
sudo systemctl status checkme
```

---

## Managing the Service

| Command | Description |
|---|---|
| `sudo systemctl start checkme` | Start the service |
| `sudo systemctl stop checkme` | Stop the service |
| `sudo systemctl restart checkme` | Restart the service |
| `sudo systemctl status checkme` | Check current status |
| `sudo systemctl enable checkme` | Enable autostart on boot |
| `sudo systemctl disable checkme` | Disable autostart on boot |

---

## Viewing Logs

View live logs (useful for debugging):
```bash
journalctl -u checkme -f
```

View last 100 lines:
```bash
journalctl -u checkme -n 100
```

View logs since last boot:
```bash
journalctl -u checkme -b
```

---

## Disabling Autostart

If you need to go back to manual mode (e.g. for development):

```bash
sudo systemctl stop checkme
sudo systemctl disable checkme
```

Then run manually as usual:
```bash
cd /home/pi/CheckMe/raspi_code
source venv/bin/activate
python main.py
```

---

## Troubleshooting

**Service fails to start — `WorkingDirectory` error**
- Double check the path in your `.service` file matches your actual project directory
- Run `ls /your/path/main.py` to verify

**Service starts but LCD shows nothing**
- The service may be starting before GPIO is ready
- Add a small delay by changing `RestartSec=5` to `RestartSec=10`
- Or add `After=network.target local-fs.target` to the `[Unit]` section

**`config/.env` not found**
- Confirm `WorkingDirectory` in the service file points to the folder that contains the `config/` directory
- The app loads `.env` using relative paths, so the working directory must be correct

**`config/firebase-credentials.json` not found**
- Same as above — confirm `WorkingDirectory` is set correctly
- Confirm the file exists: `ls /your/path/config/firebase-credentials.json`

**Service keeps restarting**
- Check logs: `journalctl -u checkme -n 50`
- Look for the specific error on startup and fix it before re-enabling

**I2C / GPIO permission denied**
- Make sure the `User=pi` in the service file matches the user that has GPIO access
- Add the user to the `gpio` and `i2c` groups if needed:
  ```bash
  sudo usermod -aG gpio,i2c pi
  ```
  Then reboot.