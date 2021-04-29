from cli import executep, execute, configurep, cli
import re
import urllib.request

print("\n *** Sample ZTP Day0 Python Script *** \n")

print("\n *** Configuring SSH access *** \n")
configurep(["username temp privilege 15 secret temp"])
configurep(["ip domain name test.local", "hostname RTR"])
configurep(["crypto key gen rsa mod 2048"])
configurep(["line vty 0 4", "login local", "transport input all", "exec-timeout 15", "end"])

print("\n ***Getting Serial number ( identifier ) *** \n")
sn = execute("sh ver | i board ID")
sn = re.split(r'\s', sn)[3]
print("SERIAL NUMBER : {}".format(sn))

print("\n ***Call back for config and provide identifier (SN)  *** \n")
url = "http://10.1.1.10/get_config"
headers = {'Serial': sn}
req = urllib.request.Request(url=url, headers=headers)
response = urllib.request.urlopen(req)
response = response.read()
print("RESPONSE : {}".format(response))
print("\n *** ZTP Day0 Python Script Execution Complete *** \n")


