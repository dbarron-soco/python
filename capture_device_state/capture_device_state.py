"""
Script Name:    capture_device_state.py
Author:         Daniel Barron
Date:           8/12/2025
Description:    Captures the state of a device. Can be used before and after network changes to confirm stability.
"""

import logging
from datetime import datetime
from netmiko import ConnectHandler
from getpass import getpass

# Prompt for credentials and device info
username = input("Enter your username: ")
password = getpass("Enter your password: ")
hostname = input("Enter the device hostname or IP address: ")

# Setup logging
log_filename = f"{hostname}_device_capture.log"
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Define device parameters
device = {
    'device_type': 'cisco_ios',
    'host': hostname,
    'username': username,
    'password': password,
}

# List of show commands to capture device state
show_commands = [
    'show running-config',
    'show startup-config',
    'show version',
    'show inventory',
    'show environment',
    'show logging',
    'show ip interface brief',
    'show interfaces',
    'show interfaces status',
    'show controllers',
    'show ip route',
    'show ip protocols',
    'show arp',
    'show mac address-table',
    'show spanning-tree',
    'show access-lists',
    'show ip nat translations',
    'show ip dhcp binding',
    'show aaa',
    'show processes cpu',
    'show processes memory',
    'show interfaces counters errors',
    'show platform'
]

# Timestamped output file
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_filename = f'device_state_{hostname}_{timestamp}.txt'

# Connect and execute commands
try:
    connection = ConnectHandler(**device)
    logging.info(f"Successfully connected to {hostname}")
    print(f"\nConnected to {hostname}\n")

    with open(output_filename, 'w') as f:
        f.write(f"Device State Capture for {hostname} - {timestamp}\n\n")
        for command in show_commands:
            try:
                output = connection.send_command(command)
                f.write(f"{'='*60}\nOutput of '{command}':\n{'='*60}\n{output}\n\n")
                logging.info(f"Executed command: {command}")
            except Exception as cmd_error:
                logging.error(f"Error executing command '{command}': {cmd_error}")
                f.write(f"Error executing command '{command}': {cmd_error}\n\n")

    connection.disconnect()
    logging.info(f"Disconnected from {hostname}")
    print(f"\nDisconnected from {hostname}")
    print(f"Device state saved to {output_filename}")

except Exception as conn_error:
    logging.error(f"Connection to {hostname} failed: {conn_error}")
    print(f"Connection to {hostname} failed. Error: {conn_error}")
