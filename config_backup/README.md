# 📦 Cisco IOS Configuration Backup Script

This Python script automates the process of connecting to a Cisco IOS device, retrieving its running configuration, and securely backing it up to a specified network location. It's ideal for network engineers and sysadmins who want a quick and repeatable way to archive device configurations.

---

## 🚀 Features

- Connects to Cisco IOS devices using SSH
- Retrieves the full running configuration
- Saves the config to a temporary local file
- Copies the file to a designated network location
- Cleans up the temporary file after transfer

---

## 🛠 Requirements

- Python 3.6+
- Cisco IOS device with SSH access
- `.env` file containing credentials

### Python Packages

Install dependencies using pip:

```bash
pip install netmiko environs
```

---

## 🔐 Environment Setup

Create a `.env` file in the root directory with the following variables:

```env
username=your_ssh_username
password=your_ssh_password
```

---

## 📁 Usage

1. Clone the repository and navigate to the script directory.
2. Run the script:

```bash
python backup_config.py
```

3. Enter the hostname or IP address of the Cisco device when prompted.
4. The script will:
   - Connect to the device
   - Save the configuration to `./temp_files/<hostname>_backup.cfg`
   - Copy it to your specified network location
   - Delete the temporary file

> ⚠️ **Important**: Replace the placeholder in the script:
>
> ```python
> destination = r'<Include the full path to your network location here>'
> ```
> with the actual path where you want the backup stored.

---

## 📌 Notes

- Ensure the target device allows SSH and your credentials have sufficient privileges.
- The script uses `terminal length 0` to prevent paginated output.
- Network location must be accessible from the machine running the script.
