from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.functions.text import print_result
from ncclient import manager
import argparse
import getpass
import warnings
import time

NTP_ENABLE = """
        <config>
          <system {}>
            <ntp xmlns="http://www.ciena.com/ns/yang/ciena-ntp">
                <admin-state>enabled</admin-state>
            </ntp>
          </system>
        </config>"""

NTP_ADD_SERVERS = """
                <config>
                  <system {}>
                    <ntp xmlns="http://www.ciena.com/ns/yang/ciena-ntp">
                        <associations>
                            <remote-ntp-server>
                                <server-entry>
                                    <address>216.239.35.0</address>
                                    <admin-state>enabled</admin-state>
                                </server-entry>
                                <server-entry>
                                    <address>37.187.5.167</address>
                                    <admin-state>enabled</admin-state>
                                </server-entry>
                            </remote-ntp-server>
                        </associations>
                    </ntp>
                  </system>
                </config>"""

v18x = 'xmlns="urn:ietf:params:xml:ns:yang:ietf-system"'
v10x = '"http://openconfig.net/yang/system"'


def check_options():
    """
    Check provided parameters

    """
    example_usage = """Example usage :
            dnfvi_ntp.py -customer LAB """

    options = argparse.ArgumentParser(description="\nCheck NTP status on DNFVI and fix if needed", epilog=example_usage)
    options.add_argument('-customer', metavar="CUSTOMER_NAME", required=True, help='Specify Customer NAME', nargs='?')

    args = options.parse_args()

    return args


def main_task(task):
    """
     Main Task

     """

    print(f'working on : {task.host.name}\n')
    conn = manager.connect(host=task.host.hostname, username=task.host.username,
                           password=task.host.password, hostkey_verify=False, timeout=10)

    # PRE-CHECKS
    # get ntp config and check if 10x or 18x system .. ffs Ciena, why do I have to do this
    res = conn.get(filter=("xpath", "//ntp"))
    if 'xmlns="http://openconfig.net/yang/system">' in str(res.xml):
        ver = v10x
    else:
        ver = v18x

    # get ntp-state and check if already in sync ... else make a change
    res = conn.get(filter=("xpath", "/ntp-state"))
    if '<synchronized>true' in str(res.xml):
        conn.close_session()
        return "NTP already in SYNC"
    else:
        # CHANGE : ADD NTP
        try:
            # enable NTP
            res = conn.edit_config(target='running', config=NTP_ENABLE.format(ver), default_operation='merge')
            if res.ok:
                # add servers
                res = conn.edit_config(target='running', config=NTP_ADD_SERVERS.format(ver), default_operation='merge')
                if not res.ok:
                    conn.close_session()
                    return "ERROR adding servers"
            else:
                conn.close_session()
                return "ERROR enabling NTP"
        except:
            conn.close_session()
            return 'Error adding NTP'

    # VALIDATE NTP settings  ...  WIP
    i = 3
    for a in range(i):
        time.sleep(5)
        res = conn.get(filter=("xpath", "/ntp-state"))
        if '<synchronized>true' in str(res.xml):
            conn.close_session()
            return "NTP in SYNC"

    return "Added servers not reachable or in sync after 30 sec"


def main():
    # suppress self-signed cert HTTPS warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    opt = check_options()
    bpo = {
        "ip": input('Enter bpo IP : '),
        "user": input('Enter bpo username : '),
        "pass": getpass.getpass(f'Enter bpo user password: '),
        "tenant": opt.customer if opt.customer else input(f'Enter bpo tenant : ')
    }

    devices = InitNornir(core={"num_workers": 20},
                         inventory={"plugin": "custom_inventory.BpoInventory",
                                    "options": {
                                        "bpo_ip": bpo["ip"],
                                        "bpo_user": bpo["user"],
                                        "bpo_pass": bpo["pass"],
                                        "bpo_tenant": bpo["tenant"],
                                    }
                                    })

    filt_dev = devices.filter(F(groups__any=["DNFVI"]))
    # import ipdb; ipdb.set_trace()

    try:
        devices.inventory.groups["DNFVI"].username = "zxcv"
        devices.inventory.groups["DNFVI"].password = getpass.getpass(f'Enter DNFVI netconf user password: ')
    except (TypeError, KeyError):
        print("Error populating credentials, verify if adequate groups are present in custom inventory")

    print("calling task ...")
    result = filt_dev.run(name="MAIN TASK", task=main_task)
    print("ALL DONE.")

    print_result(result)

    return


if __name__ == "__main__":
    main()
