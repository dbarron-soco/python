import logging
from getpass import getpass
from netmiko import ConnectHandler
from datetime import datetime

# Prompt for credentials and device info
username = input("Enter your username: ")
password = getpass("Enter your password: ")
hostname = input("Enter the device hostname or IP address: ")

# Setup logging
log_filename = f'{hostname}port_description_sync.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Define device parameters
device = {
    'device_type': 'cisco_ios',
    'host': hostname,
    'username': username,
    'password': password,
}

try:
    # Connect to the device
    connection = ConnectHandler(**device)
    logging.info(f"Connected to {hostname}")
    print(f"\nConnected to {hostname}\n")

    # Try CDP first
    cdp_output = connection.send_command("show cdp neighbors detail")
    if "CDP is not enabled" in cdp_output or not cdp_output.strip():
        # Try LLDP if CDP is not available
        lldp_output = connection.send_command("show lldp neighbors detail")
        if "LLDP is not enabled" in lldp_output or not lldp_output.strip():
            logging.warning("Neither CDP nor LLDP is enabled on the device.")
            print("Neither CDP nor LLDP is enabled on the device.")
            connection.disconnect()
            exit()
        else:
            neighbor_data = lldp_output
            protocol = "LLDP"
    else:
        neighbor_data = cdp_output
        protocol = "CDP"

    logging.info(f"Using {protocol} neighbor data")

    # Parse neighbor data
    interface_map = {}
    for line in neighbor_data.splitlines():
        if "Interface:" in line and "Port ID" in line:
            parts = line.split(",")
            local_intf = parts[0].split("Interface:")[1].strip()
            remote_port = parts[1].split("Port ID (outgoing port):")[1].strip()
        elif "Device ID:" in line:
            remote_device = line.split("Device ID:")[1].strip()
            description = f"Connected to {remote_device} via {remote_port}"
            interface_map[local_intf] = description

    # Apply interface descriptions
    config_commands = []
    for intf, desc in interface_map.items():
        config_commands.extend([
            f"interface {intf}",
            f"description {desc}"
        ])
        logging.info(f"Prepared description for {intf}: {desc}")

    if config_commands:
        connection.send_config_set(config_commands)
        logging.info("Interface descriptions updated successfully.")
        print("Interface descriptions updated successfully.")
    else:
        logging.info("No neighbor data found to update descriptions.")
        print("No neighbor data found to update descriptions.")

    connection.disconnect()
    logging.info(f"Disconnected from {hostname}")
    print(f"\nDisconnected from {hostname}")

except Exception as e:
    logging.error(f"Error occurred: {e}")
    print(f"An error occurred: {e}")
