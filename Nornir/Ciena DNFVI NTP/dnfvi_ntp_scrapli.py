from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.functions.text import print_result
from scrapli.driver import GenericDriver
import argparse
import getpass
import warnings
import time


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
    device = {
        "host": task.host.hostname,
        "auth_username": task.host.username,
        "auth_password": task.host.password,
        "auth_strict_key": False,
        "transport": "paramiko",
        "port": 830,
        "timeout_socket": 2
    }

    with GenericDriver(**device) as conn:

        # conn.send_command('yp-shell')
        prompt = conn.get_prompt()
        if "@NFV-FRU>" not in prompt:
            conn.close()
            return " 10x system .. check manually"

        # PRE-CHECKS
        command = 'sget /ntp-state'
        res = conn.send_command(command)

        if '"synchronized":true' in res.result:
            conn.close()
            return "Already in SYNC"
        else:
            # CHANGE : ADD NTP
            command = 'config t'
            conn.send_command(command)

            command = 'sys:system ciena-ntp:ntp admin-state enabled'
            res = conn.send_command(command)
            if "failed" in res.result:
                conn.close()
                return " Error enabling NTP ... inspect manually"

            serv = "216.239.35.0"
            srv_added = False
            command = 'sys:system ciena-ntp:ntp associations remote-ntp-server server-entry 216.239.35.0 admin-state enabled'
            res = conn.send_command(command)
            #  cover case where we don't have "applied" in output and where we do have "applied" but we also have failed
            if 'Applying 1 edit' not in res.result or "failed" in res.result:
                print(f'{task.host.name}: Error applying config for {serv}')
            else:
                srv_added = True

            serv = "37.187.5.167"
            command = 'sys:system ciena-ntp:ntp associations remote-ntp-server server-entry 37.187.5.167 admin-state enabled'
            res = conn.send_command(command)
            conn.send_command('exit')
            if 'Applying 1 edit' not in res.result or "failed" in res.result:
                print(f'{task.host.name}: Error applying config for {serv}')
            else:
                srv_added = True
            if srv_added:
                conn.close()
                return " Error adding servers "

        # VALIDATE NTP settings
        i = 3
        for j in range(i):
            time.sleep(5)  # wait 5 seconds for dnfvi to contact NTP server to have server-state : reach
            command = 'sget /ntp-state'
            res = conn.send_command(command)
            if '"server-state":"reach"' in res.result:
                time.sleep(5)  # wait 5 more seconds to have them in sync
                res = conn.send_command(command)
                if '"synchronized":true' in res.result:
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
        devices.inventory.groups["DNFVI"].username = "asdf"
        devices.inventory.groups["DNFVI"].password = getpass.getpass(f'Enter DNFVI user "user" password: ')
    except (TypeError, KeyError):
        print("Error populating credentials, verify if adequate groups are present in custom inventory")

    print("calling task ...")
    result = filt_dev.run(name="MAIN TASK", task=main_task)
    print("ALL DONE.")

    print_result(result)

    return


if __name__ == "__main__":
    main()
