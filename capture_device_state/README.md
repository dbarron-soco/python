# capture_device_state.py

Capture a comprehensive snapshot of a Cisco device’s operational state — ideal for **pre‑change** and **post‑change** validation during maintenance windows or incident response.

> **Author:** Daniel Barron  
> **Created:** August 12, 2025

---

## ✨ What this script does

- Prompts for **credentials** and a **target device** (hostname/IP).
- Establishes an SSH session via **Netmiko**.
- Executes a curated list of **show** commands that reflect device health, configuration, routing, interfaces, and platform status.
- Writes all command outputs to a **timestamped text file** and logs actions to a **.log** file.

---

## ✅ Features

- **Safe by default**: credentials are entered interactively (not stored in code).
- **Self-documenting capture**: outputs are separated and clearly labeled per command.
- **Simple logging**: connection success/errors and per‑command execution are logged.
- **Ready for change control**: run **before** and **after** a change and diff the outputs.

---

## 📦 Requirements

- **Python**: 3.8+ recommended
- **Packages**:
  - [`netmiko`](https://pypi.org/project/netmiko/) (brings in `paramiko` for SSH)
- **Network/Device**:
  - SSH enabled on the device
  - Reachability (routing/ACLs) from your workstation to the device
  - Account with sufficient privilege (see **Enable/Privilege Notes** below)

Install dependencies:

```bash
# (Recommended) in a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install --upgrade pip
pip install netmiko
```

---

## 🧰 Supported Platforms

This script is configured for **Cisco IOS** (`device_type='cisco_ios'`).  
It may also work on **IOS XE** targets using the same device type.

> For **NX‑OS** or other vendors, you’ll need to:
> 1) change `device_type`, and  
> 2) adjust the command list to match that platform’s CLI.

---

## 🚀 Usage

From the folder containing `capture_device_state.py`:

```bash
python capture_device_state.py
```

You will be prompted for:

```
Enter your username: <your_username>
Enter your password: ********
Enter the device hostname or IP address: 10.10.10.10
```

On success, you’ll see:

```
Connected to 10.10.10.10

Disconnected from 10.10.10.10
Device state saved to device_state_10.10.10.10_YYYYMMDD_HHMMSS.txt
```

### Output Artifacts

- **`device_state_<hostname>_<timestamp>.txt`**  
  A single, readable text file containing all command outputs, each section delimited and labeled.
- **`<hostname>_device_capture.log`**  
  A log file noting connection status and command execution results.

---

## 📄 Commands Captured

The script runs the following **show** commands:

```
show running-config
show startup-config
show version
show inventory
show environment
show logging
show ip interface brief
show interfaces
show interfaces status
show controllers
show ip route
show ip protocols
show arp
show mac address-table
show spanning-tree
show access-lists
show ip nat translations
show ip dhcp binding
show aaa
show processes cpu
show processes memory
show interfaces counters errors
show platform
```

> ⚠️ Some commands may not exist or may vary across platforms/images. Unsupported commands will be logged and noted in the output file without interrupting the full capture.

---

## 🔐 Enable / Privilege Notes

Many commands require **privileged EXEC** (enable) or **privilege 15**. The current script does **not** send `enable`.  
You have two options:

1) **Log in with a privilege 15 account**, _or_  
2) **Add enable support**:

```python
# Add to device dict:
' secret': '<enable_password>'

# After connecting and before sending commands:
connection.enable()
```

> **Security best practice:** Avoid hardcoding secrets. Prefer prompting (as done here), environment variables, or a secrets manager.

---

## 🔁 Pre‑Change / Post‑Change Diff Workflow

1. **Before** the change:  
   ```bash
   python capture_device_state.py
   # Produces device_state_HOSTNAME_YYYYMMDD_HHMMSS.txt
   ```

2. **After** the change:  
   ```bash
   python capture_device_state.py
   ```

3. **Compare** the two files:

   - macOS / Linux:
     ```bash
     diff -u device_state_host_pre.txt device_state_host_post.txt | less
     ```
   - Windows (PowerShell):
     ```powershell
     Compare-Object (Get-Content .\device_state_host_pre.txt) (Get-Content .\device_state_host_post.txt) -SyncWindow 5
     ```

> Tip: Keep a small, **critical-commands-only** list for high-signal diffs (e.g., `show running-config`, `show ip route`, `show interfaces status`, `show logging`).

---

## 🛠️ Extending the Script

### Add or Remove Commands
Edit the `show_commands` list to tailor capture depth to your device role and platform.

### Support Another Platform (e.g., NX‑OS)
- Change:
  ```python
  'device_type': 'cisco_nxos'
  ```
- Update commands (e.g., replace `show ip interface brief` with `show interface brief`, etc.).

### Non-Interactive Credentials (Optional)
If you need unattended runs (e.g., in a CI runner), consider sourcing credentials from environment variables.  
> **Use with caution** and follow your organization’s secrets policy.

---

## 🧯 Troubleshooting

- **`Connection failed`**
  - Verify SSH reachability (ACLs, routing, VRFs).
  - Confirm device SSH is enabled (`ip ssh version 2`, `transport input ssh`).
  - Check username/password and privilege level.

- **`Some commands fail`**
  - The device OS may not support them. Remove or replace those commands.
  - Ensure privilege 15 or add `secret` + `connection.enable()`.

- **Empty or partial output**
  - Increase Netmiko read timeout (advanced: pass `global_delay_factor` or per-command `delay_factor`).
  - Ensure the terminal length isn’t paging output (Netmiko typically handles this, but images differ).

- **Log file not created**
  - Confirm write permissions in the working directory.
  - File name is derived from the hostname you entered.

---

## 📂 Project Structure

```
.
├── capture_device_state.py
├── device_state_<hostname>_<timestamp>.txt   # generated
└── <hostname>_device_capture.log             # generated
```

---

## 🧭 Roadmap Ideas (Nice-to-haves)

- `argparse` CLI flags (e.g., `--host`, `--user`, `--commands-file`, `--platform`).
- Read device inventory from CSV/YAML and iterate across multiple hosts.
- Built-in **pre/post diff** and HTML report generation.
- Pluggable command packs per platform/role.
- Optional redaction for sensitive config lines.

---

## 🤝 Contributing

Issues and PRs are welcome!  
Please:
- Note platform/version tested.
- Include logs and sanitized outputs for debugging where applicable.
- Avoid committing any secrets or sensitive configs.

---
