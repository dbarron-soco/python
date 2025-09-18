Capture Device State
Author: Daniel Barron
Date: 08/12/2025

📌 Overview
capture_device_state.py is a Python script designed to capture the current state of a Cisco IOS device. It is particularly useful for pre-change and post-change validation, ensuring network stability and providing a snapshot of device configurations and operational status.

✅ Features
Prompts for username, password, and device hostname/IP.
Connects to Cisco IOS devices using Netmiko.
Executes a predefined set of show commands to gather:
Running and startup configurations
Hardware and software details
Interface status and errors
Routing, ARP, MAC tables
CPU and memory utilization
Saves output to a timestamped text file.
Logs all actions and errors to a log file.
🛠 Requirements
Python 3.7+
Netmiko
Standard Python libraries: logging, datetime, getpass
Install dependencies:




Shell
pip install netmiko

▶️ Usage
Clone the repository:




Shell
git clone https://github.com/<your-username>/capture-device-state.git
cd capture-device-state

Run the script:




Shell
python capture_device_state.py

Enter:

Username
Password (hidden input)
Device hostname or IP address
The script will:

Connect to the device
Execute a series of show commands
Save the output to:
device_state_<hostname>_<timestamp>.txt
Log details in:
<hostname>_device_capture.log
📂 Output Example
Device State Capture for switch01 - 20250918_090000

============================================================
Output of 'show running-config':
============================================================
<running-config output>

============================================================
Output of 'show version':
============================================================
<version output>
⚠️ Notes
This script is intended for Cisco IOS devices. For other platforms, modify the device_type in the script.
Ensure you have SSH access to the device.
Use in a secure environment; credentials are entered interactively and not stored.
✅ To-Do / Future Enhancements
Add support for multiple devices via a CSV input.
Include error handling for unreachable devices.
Option to export results in JSON or structured format.
Add pre/post-change diff comparison feature.
