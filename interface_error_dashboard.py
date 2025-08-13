"""
Script Name:    interface_error_dashboard.py
Author:         Daniel Barron
Date:           8/12/2025
Description:    Connects to a Cisco device, runs show interfaces counters errors, parses the output, and displays a dashboard highlighting interfaces with high error counts.
"""

import logging
from getpass import getpass
from netmiko import ConnectHandler
from datetime import datetime
from tabulate import tabulate

# Setup logging
log_filename = 'interface_error_dashboard.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Prompt for credentials and device info
username = input("Enter your username: ")
password = getpass("Enter your password: ")
hostname = input("Enter the device hostname or IP address: ")
error_threshold = int(input("Enter the error count threshold to flag interfaces: "))

# Define device parameters
device = {
    'device_type': 'cisco_ios',
    'host': hostname,
    'username': username,
    'password': password,
}

# Connect and retrieve interface error statistics
try:
    connection = ConnectHandler(**device)
    logging.info(f"Connected to {hostname}")
    print(f"\nConnected to {hostname}\n")

    output = connection.send_command("show interfaces counters errors")
    connection.disconnect()
    logging.info(f"Disconnected from {hostname}")
    print(f"\nDisconnected from {hostname}\n")

    # Parse the output
    lines = output.splitlines()
    headers = []
    data = []
    for line in lines:
        if "Port" in line and "Align-Err" in line:
            headers = line.split()
        elif line and not line.startswith("Port"):
            fields = line.split()
            if len(fields) == len(headers):
                entry = dict(zip(headers, fields))
                data.append(entry)

    # Filter interfaces with high error counts
    flagged = []
    for entry in data:
        total_errors = sum(int(entry.get(col, '0')) for col in headers[1:] if entry.get(col, '0').isdigit())
        if total_errors >= error_threshold:
            entry['Total Errors'] = total_errors
            flagged.append(entry)

    # Display dashboard
    print(f"Interface Error Dashboard for {hostname} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    if flagged:
        print(tabulate(flagged, headers="keys", tablefmt="grid"))
    else:
        print("No interfaces exceeded the error threshold.")

except Exception as e:
    logging.error(f"Error occurred: {e}")
    print(f"An error occurred: {e}")
