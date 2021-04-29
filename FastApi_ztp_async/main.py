"""
    Provisioning server
        - serve initial config script
        - capture the callback with device SN
        - based on SN query inventory ( yaml mock + netbox partialy for now ) generate config for device
        - push config to device
        - perform some basic tests (TO DO)
        - add device to PRTG monitoring
"""

import asyncio
import httpx
import warnings
import pprint
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import FileResponse
from ruamel.yaml import YAML
from scrapli.driver.core import AsyncIOSXEDriver
from jinja2 import Environment, FileSystemLoader
import logging
import ipaddress
import sys


# filter https unsigned cert warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Logger setup
LOG_FILE = 'main.log'
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime) %(name)s - %(levelname)s - %(message)s"
)

# General API param dict
#    Dict that contains info about various APIs
#     including auth parameters
API = {
    "prtg": {
        "url": "http://10.1.1.13/api/",
        "name": "PRTG",
        "username": "prtgadmin",
        "passhash": "2143531094"
    },
    "netbox": {
        "url": "https://10.1.1.12/api/",
        "name": "NETBOX",
        "token": "1234567f70e0d13bac2525dc1234566789fc69b5a"
    }
}

#  Specific API params
#       PRTG params

GROUPID = 2050  # Group where new device will be
CLONEDEVID = 2051  # Device to be cloned
PRTG = {
    "delete": "deleteobject.htm",
    "duplicate": "duplicateobject.htm",
    "historicdata": "historicdata.json",
    "discover": "discovernow.htm",
    "scan": "scannow.htm",
    "pause": "pause.htm",
    "table": "table.json",
}

#       Netbox params
NETBOX = {
    "devices": "dcim/devices/",
    "device": "/dcim/devices/{}/"
}

# ZTP params
ztp_conf = "script.py"  # name of the static file being served (should be in the same folder ... or give path)
app = FastAPI()


async def main_config(device: dict):
    """
    - Get detailed device info from inventory ( yaml mock for now ... TO DO : get full from netbox) ... async
	- generate config from device info using jinja template .. async
    - Connect to device ( scrapli async ), push the rest of the config
    - TO DO perform some tests from device ( scrapli )and add device to PRTG ... async

    :param: device: dict - dict with basic device info
    :return:
    """

    print(f"\n get device info from yaml inventory \n")
    dev_info = await _get_device_data(device['serial'])

    env = Environment(loader=FileSystemLoader('.'), enable_async=True)
    template = env.get_template("config.j2")
    print(f"\n Render data with Jinja2 template \n")
    logging.info(f"Rendering data for device with SN : {device['serial']}")
    config = str(await template.render_async(device=dev_info)).splitlines()
    # pprint.pprint(config)  # dbg

    print(f" \n Scrapli async part ... push config to device \n")
    rtr = {
        "host": device['device_IP'],
        "auth_username": "temp",
        "auth_password": "temp",
        "auth_strict_key": False,
        "transport": "asyncssh",
    }

    # wait for router to exit guestshell and complete the boot process because you cant ssh to it before that
    for i in range(3):
        print(f"\nWaiting for RTR to finish booting\n")
        logging.info("Waiting 30 sec for device to complete booting")
        await asyncio.sleep(30)
        try:
            async with AsyncIOSXEDriver(**rtr) as conn:
                logging.info(f"sending config to device with SN : {device['serial']}")
                results3 = await conn.send_configs(configs=config, failed_when_contains=["Invalid input detected"],
                                                   stop_on_failed=True, timeout_ops=5)
                pprint.pprint(f"RESULT 3 : {[result.result for result in results3]}")  # dbg
                # get some verification commands
                results1 = await conn.send_commands(["show int des", "sh ip route", "sh ip int brie"])
                pprint.pprint([result.result for result in results1])
                break
        except:
            print(f"\nUnable to ssh to device .. waiting another 30 sec\n")
            logging.info(f"Unable to ssh to dev with SN {device['serial']}, waiting for another 30 sec")

    print(f"\nAdding device to PRTG\n")
    try:
        await prtg_add(device['device_IP'], dev_info['location'])
        logging.info(f"adding device with SN : {device['serial']} to PRTG")
    except:
        print(f"Failed to add a device : Error - {sys.exc_info()[0]}")

    return


async def apiget(api: dict, apicall: str, *args, **kwargs):
    """
    General GET request fn

    :param api: api dict with api params
    :param apicall: specific api call from API_CALL dict
    :param kwargs: parameters dict passed to the call .. minus auth params
    :return: depending on the api call ... json or str

    example : await apiget(API['prtg'], PRTG["delete"], id=1234, approve=1)
              await apiget(API['netbox'], NETBOX['devices'], serial=sn)
              await apiget(API['netbox'], NETBOX['device'], "12345678")

    """
    if not args:
        call = apicall
    else:
        call = apicall.format(args[0])

    url = f"{api['url']}{call}"
    params = {}
    headers = {}

    # extract parameters from kwargs and populate params
    if kwargs:
        for key, value in kwargs.items():
            params.update({key: value})
    elif "PRTG" in api['name']:
        raise Exception("no Parameters provided, PRTG API needs params")

    # add AUTH parameters
    if "PRTG" in api['name']:
        params.update({
            "username": api['username'],
            "passhash": api['passhash']
        })
    elif "NETBOX" in api['name']:
        headers.update({
            "Authorization": f"Token {api['token']}"
        })

    res = ''

    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(url, headers=headers, params=params)

    if r.status_code == 200:
        if ".json" in apicall:  # prtg specific
            res = r.json()
        elif "htm" in apicall:  # prtg specific
            res = "OK"
        else:
            res = r.json()  # general / netbox
    else:
        res = "... some ERROR ..."
        # print(r.status_code)

    # print(res)  # dbg

    return res


async def prtg_add(ip: str, name: str):
    """
    Add device to PRTG monitoring

    :param ip: new device IP
    :param name: device name
    :return:
    """
    # add device ( there is no add device api so adding is done by cloning existing ( new name and IP )
    await apiget(API['prtg'], PRTG["duplicate"], id=CLONEDEVID, name=name, host=ip, targetid=GROUPID)

    # get new device ID
    dev_id = await apiget(API['prtg'], PRTG["table"], content='probes', output='json', columns='objid,name',
                          filter_parentid=GROUPID, filter_name=name)
    dev_id = int(dev_id['probes'][0]['objid'])

    # unpause auto discovery for newly created device ( its paused when crated via api )
    await apiget(API['prtg'], PRTG["pause"], id=dev_id, action=1)

    return


async def _get_device_data(sn: str) -> dict:
    """
    Get device config ( from yaml file and from netbox ) based on SN

    :param sn: str - device serial number
    :return: dict with device details
    """
    result = {}
    nbox_dev = {}

    with open("inventory.yaml", "r") as f:
        logging.info(f"yaml inventory opened looking for SN : {sn}")
        inventory = YAML()
        devices = inventory.load(f)

    for dev in devices:
        if sn in str(devices[dev]['serial']):
            result = devices[dev]
            logging.info(f"found yaml data for SN : {sn}")
            break

    try:
        nbox_dev = await apiget(API['netbox'], NETBOX['devices'], serial=sn)
        nbox_dev = nbox_dev['results'][0]
        print(f"""\n
            Some Netbox inventory results : 
            SN : {nbox_dev['serial']}
            prim_IP: {ipaddress.IPv4Interface(str(nbox_dev["primary_ip4"]["address"])).ip}
            prim_MASK: {ipaddress.IPv4Interface(str(nbox_dev["primary_ip4"]["address"])).netmask}
            name : {nbox_dev["name"]}
            sitename : {nbox_dev["site"]["name"]}
            \n""")  # dbg
        result['location'] = nbox_dev["site"]["name"]
        logging.info(f" Device with sn {sn} found in inventory and data retrieved")
    except:
        print("\n Netbox device data GET failed ( no device found, key error or connection error) \n")
        print(f"Error : {sys.exc_info()[0]}")

    return result


@app.get("/script.py")
async def init_script(req: Request):
    """
    Get initial boot script request, check data and give appropriate file

    currently it just serves the file

    :param req: GET request
    :return: Initial config py file
    """
    # pprint.pprint(f"HEADERS: {req.headers}")
    # pprint.pprint(f"SOURCE IP : {req.client.host}")
    logging.info(f"SERVE INIT SCRIPT to {req.client.host}")
    print("\n SERVE INIT SCRIPT")

    return FileResponse(ztp_conf)


@app.get("/get_config")
async def get_config(req: Request, background_tasks: BackgroundTasks):
    """
    Listen for callbacks, extract basic info and engage a separate config process

    :param req:
    :param background_tasks:
    :return: status for caller to print ...
    """
    # pprint.pprint(f"HEADERS: {req.headers}")
    # pprint.pprint(f"SOURCE IP : {req.client.host}")

    basic_info = {
        "device_IP": req.client.host,
        "serial": str(req.headers["serial"])
    }
    # print(basic_info['serial'])  # dbg
    logging.info(f"Received SN from device: DEV: {basic_info['device_IP']}  SN: {basic_info['serial']}")
    print(f"\n Sending config task to Background")
    background_tasks.add_task(main_config, basic_info)

    return {'Status': 'Request sent for further processing'}
