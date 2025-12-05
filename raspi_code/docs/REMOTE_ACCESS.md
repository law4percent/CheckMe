# Remote Desktop Access using Tailscale and RealVNC

Tailscale is like a private VPN that creates a secure network between your devices. Your Pi and PC will act as if they are on the same LAN, even if they are far apart.


## Prerequisites

1. Raspberry Pi is running (any model with internet access).

2. You can access your Pi at least locally (via monitor/keyboard or WiFi/Ethernet).

3. PC (Windows/macOS/Linux) has internet.

4. Download RealVNC


---
## Tailscale Full Guide

### STEP 1 — Install Tailscale on Raspberry Pi

1. Open a terminal on your Pi.

2. Run the install command:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

This downloads and installs the Tailscale package.

3. After installation, run:
```bash
sudo tailscale up
```

- This will open a URL for login.

- Copy that URL to a browser on your PC or phone.

- Log in with your Google, Microsoft, or GitHub account (any account Tailscale accepts).

- Authorize the Pi to join your Tailscale network.

- After successful login, your Pi is now connected to your Tailscale private network.

### STEP 2 — Install Tailscale on Your PC

1. Go to [https://tailscale.com/download](https://tailscale.com/download)

2. Download and install the Tailscale client for your OS.

3. Log in using the same account you used for your Pi.

Now your PC and Pi are on the same private network — even if they are thousands of miles apart.


### STEP 3 — Find your Pi’s Tailscale IP

On your Raspberry Pi terminal, type:
```bash
tailscale ip
```

- You’ll see something like:
```bash
100.00.22.14
```

- This is a private IP that only works inside your Tailscale network.


### STEP 4 — SSH into your Pi from anywhere

On your PC terminal:
```bash
ssh pi@<tailscale-ip>
```

Example:
```bash
ssh pi@100.81.22.14
```

- Enter your Pi password.

- You are now remotely connected via SSH, even over mobile data.


### STEP 5 — Optional: Connect VNC over Tailscale

If you want GUI access:

1. Make sure VNC server is enabled on your Pi.

2. Connect via **VNC Viewer** to the **Tailscale IP** of the Pi instead of local LAN IP.

No port forwarding is needed — it’s fully secure.


---
## RealVNC Full Guide


### STEP 1 — Enable VNC on Raspberry Pi

**Option A: Using Raspberry Pi with a Monitor**
1. Open Raspberry Pi Configuration
`Menu → Preferences → Raspberry Pi Configuration`
2. Go to Interfaces tab
3. Turn VNC → Enabled

**Option B: Headless Mode (No monitor)**
If you don’t have a Raspi monitor/LCD screen:
1. Connect to Pi via SSH
Example:
```bash
ssh pi@<your_pi_ip>
```

2. Run:
```bash
sudo raspi-config
```

3. Go to:
```bash
Interface Options → VNC → Enable
```


### STEP 2 — Install VNC Viewer on Your PC
Download from RealVNC:

Search Search “RealVNC **Viewer download”** 
OR
([Open this link to download](https://www.realvnc.com/en/connect/download/viewer/))


### STEP 3 — Get the Raspberry Pi’s IP Address
On the Raspberry Pi (SSH or terminal):
```bash
hostname -I
```
Example output: `192.168.1.23`
Keep the IP to connect.

Use the Tailscale to connect remotetly ([This can be find to the top](#step-3--find-your-pis-tailscale-ip))



### STEP 4 — Connect from Your PC
1. Open VNC Viewer

2. Enter the Pi's IP address: `192.168.1.23`

3. Log in using your Raspberry Pi user credentials:

- Username: usually pi

- Password: the one you set

- You should now see your Raspberry Pi desktop.