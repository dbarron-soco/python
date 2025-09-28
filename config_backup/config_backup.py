from netmiko import ConnectHandler
import shutil
import os
from environs import Env


env = Env()     # Initialize the Env object
env.read_env()  # Read the .env file


#Declare global variables.

username = env("username")
password = env("password")
hostname = input("Hostname: ")                                                        

path = "./temp_files/" + hostname + "_backup.cfg"    # Specifies the location your file will be held before copy.

device = {
    'device_type': 'cisco_ios',
    'host':   hostname,
    'username': username,
    'password': password,
}

net_connect = ConnectHandler(**device)
output = net_connect.send_command('terminal length 0')
output = net_connect.send_command('show run')
with open(path, 'w') as f:                   #This is the script writing the configuration file.
    f.write(output)
    f.close

#This copies the config file to a specified network location.
source = path
destination = r'<Include the full path to your network location here>'
shutil.copy(source, destination)     # Moves the file
os.remove(source)    # Deletes the initial file that was created.

print ("Your config has been copied to <" + destination + ">")
