### Provisioning IOS XE using ZTP, FastAPI, Netbox, Scraply


In this sim a single VM ( CentOS7 ) is running as DHCP server, HTTP server ( serving init script and listening for callback ) and "config" server 

Setup : DHCP/HTTP srv: 10.1.1.10 ; RTR: dhcp (10.1.1.50-100) ; Netbox : 10.1.1.12 ; PRTG : 10.1.1.13

FastAPI is used for serving requests (async). Comunication with other APIs is async using httpx, SSH connection is async ( Scrapli async)

GNS3 running csr1000v 17.03.02

Router G1 interface is bridged to server interface ( LAN segment )


Server requirements:

    
    1. Install python 3.8+
    
    2. Install dependencies pip3.8 install -r requirements.txt
    
    3. Ensure scipt.py, config.j2, inventory.yaml, main.py are in the same folder
    
    4. Edit script.py to call back to proper IP ... edit inventory.yaml and add SN of the routers you are deploying ( this is a mock of inventory )
    
    5. Run the uvicorn server
        
        uvicorn main:app --host < SERVER IP > --port 80
    
    6. Loga can be found in main.log file
        


General process flow:

	Pre-work task: Deploy a router in GNS3 (4GB+ RAM)... collect SN manualy and update one of the devices 
	in inventory.yaml and update Netbox device SN
		
	1. [ Server ] Run uvicorn server, ensure dhcp is serving the correct file ( SERVER IP/script.py )
	2. [ Router ] Router boots up, gets IP and option 67 from DHCP
	3. [ Router ] Router collects the file
	4. [ Router ] script.py is being executed on the router
		4.1. Add temp user and SSH enable config
		4.2. [ Optional ] Add some config that can break ssh session if pushed remotely 
		    ( could be set with custom init script download on server)
		4.3. Get device Serial Number
		4.4. Call back the server and provide SN in the header
	5. [ Server ] Capture the device call back and collect basic info ( IP and SN ) and push it for 
	    further processing, return ACK to to device so it can finish the script and booting process
	6. [ Server ] Load (call) inventory and get device details based on SN
	7. [ Server ] Generate config for a specific device using jinja template ( CLI but can be NETCONF also)
	8. [ Server ] Wait for 30sec (async) to ensure router guestshell is closed and boot proces finished
	9. [ Server ] Connect to device via SSH (async) and push generated config (CLI but can be NETCONF also).
	10. [ Server ] Add device to PRTG monitoring

	