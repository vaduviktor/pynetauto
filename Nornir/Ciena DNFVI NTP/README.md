
####Collect inventory from BP Orchestrator, feed it to Nornir, run NTP check on all inventory devices using various methods and correct NTP settings if needed


1 ) Install Python 3.7

2 ) Install dependencies ( libs ) 

	pip install -r requirements.txt

help : 	    dnfvi_ntp_netmiko.py -h 
example:
	dnfvi_ntp_netmiko.py -customer LAB
	dnfvi_ntp_scrapli.py -customer LAB
	dnfvi_ntp_netconf.py -customer LAB
