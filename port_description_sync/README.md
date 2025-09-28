# 🔌 Cisco Interface Description Sync Script

This Python script automates the process of updating interface descriptions on Cisco IOS devices using CDP or LLDP neighbor data. It’s designed to help network engineers maintain accurate and meaningful interface documentation across their infrastructure.

---

## 🚀 Features

- Connects to Cisco IOS devices via SSH
- Retrieves neighbor information using CDP or LLDP
- Parses neighbor data to identify connected devices and ports
- Automatically updates interface descriptions
- Logs all actions and errors to a device-specific log file

---

## 🛠 Requirements

- Python 3.6+
- Cisco IOS device with SSH access
- CDP or LLDP enabled on the device

### Python Packages

Install required packages via pip:

```bash
pip install netmiko
```

---

## 🔐 Usage

1. Clone the repository and navigate to the script directory.
2. Run the script:

```bash
python sync_interface_descriptions.py
```

3. Enter your credentials and the device hostname or IP address when prompted.
4. The script will:
   - Connect to the device
   - Retrieve neighbor data using CDP or LLDP
   - Parse and apply interface descriptions
   - Log all actions to `<hostname>port_description_sync.log`

---

## 📁 Logging

All operations and errors are logged to a file named after the device:

```
<hostname>port_description_sync.log
```

This includes connection status, protocol used, configuration changes, and any exceptions.

---

## ⚠️ Notes

- Ensure CDP or LLDP is enabled on the device for neighbor discovery.
- The script uses `send_config_set()` to apply changes—make sure your user has config-level privileges.
- LLDP is used as a fallback if CDP is unavailable.
