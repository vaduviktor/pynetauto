from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.functions.text import print_result
from netmiko import ConnectHandler, redispatch
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
    conn = task.host.get_connection("netmiko", task.nornir.config)

    # print("yp-shell") # dbg
    command = 'yp-shell'
    res = conn.send_command_timing(command)
    # check if it entered yp-shell ( > ) AND if it didn't land in 10x system
    if ">" in res and "SHELL PARSER FAILURE" not in res:
        conn.set_base_prompt(pri_prompt_terminator=">", alt_prompt_terminator="#")
    else:
        print(f'{task.host.name}: Error entering yp-shell')
        task.host.close_connections()
        return " ERROR entering YP-SHELL or 10x system ... check manually "

    # PRE-CHECKS
    command = 'sget /ntp-state'
    res = conn.send_command(command)
    # print(res)  # dbg

    if '"synchronized":true' in res:
        task.host.close_connections()
        return "NTP already in SYNC"
    else:
        # CHANGE : ADD NTP

        # print("conf t") # dbg
        command = 'config t'
        conn.send_command_timing(command)
        conn.set_base_prompt(pri_prompt_terminator="#", alt_prompt_terminator=">")

        # print("ntp enable")  # dbg
        command = 'sys:system ciena-ntp:ntp admin-state enabled'
        res = conn.send_command(command, auto_find_prompt=False)
        #  if ntp enable config fail to apply exit and inspect manually
        if "failed" in res:
            print(f'{task.host.name}: Error applying ntp enable config')
            conn.send_command_timing('exit')
            conn.set_base_prompt(pri_prompt_terminator=">", alt_prompt_terminator="#")
            conn.send_command_timing('quit')
            task.host.close_connections()
            return " ERROR enabling NTP .. check manually "

        serv = "216.239.35.0"
        # print(f'set server {serv}')  # dbg
        command = 'sys:system ciena-ntp:ntp associations remote-ntp-server server-entry 216.239.35.0 admin-state enabled'
        res = conn.send_command_timing(command)
        # print(res)
        if 'Applying 1 edit' not in res or "failed" in res:
            print(f'{task.host.name}: Error applying server add config for {serv}')

        serv = "37.187.5.167"
        # print(f'set server {serv}')  # dbg
        command = 'sys:system ciena-ntp:ntp associations remote-ntp-server server-entry 37.187.5.167 admin-state enabled'
        res = conn.send_command_timing(command)
        # print(res)  # dbg
        if 'Applying 1 edit' in res and "failed" not in res:
            conn.send_command_timing('exit')
            conn.set_base_prompt(pri_prompt_terminator=">", alt_prompt_terminator="#")
        else:
            conn.send_command_timing('exit')
            conn.set_base_prompt(pri_prompt_terminator=">", alt_prompt_terminator="#")
            print(f'{task.host.name}: Error applying server add config for {serv}')

    # VALIDATE NTP settings
    i = 3
    for j in range(i):
        time.sleep(5)  # wait 5 seconds for dnfvi to contact NTP server to have server-state : reach
        command = 'sget /ntp-state'
        res = conn.send_command(command)
        # print(res)  # dbg
        if '"server-state":"reach"' in res:
            time.sleep(5)  # wait 5 more seconds to have them in sync
            res = conn.send_command(command)
            if '"synchronized":true' in res:
                conn.send_command_timing('quit')
                task.host.close_connections()
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
        devices.inventory.groups["DNFVI"].username = "diag"
        # devices.inventory.groups["DNFVI"].password = "FL#Xw4r#pR)"
        devices.inventory.groups["DNFVI"].password = getpass.getpass(f'Enter DNFVI user "diag" password: ')
    except (TypeError, KeyError):
        print("Error populating credentials, verify if adequate groups are present in custom inventory")

    print("calling task ...")
    result = filt_dev.run(name="MAIN TASK", task=main_task)
    print("ALL DONE.")

    print_result(result)

    return


if __name__ == "__main__":
    main()
