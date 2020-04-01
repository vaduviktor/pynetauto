from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.tasks import networking
from nornir.plugins.tasks.files import write_file
import argparse
import getpass
import warnings
from cnhelper import Dnfvi
import sys
"""
Run command on various devices using Nornir custom inventory ( get devices from Blue Planet ) 

"""

cmd = {
    "SAOS": {'sh_run': 'config show brief',
             'sh_ver': 'software show'},
    "vyatta": {'sh_run': 'show configuration commands',
               'sh_ver': 'show version'},
    "DNFVI": {'sh_run': 'show run',
              'sh_ver': 'show software'}
}


def check_options():
    """
    Check provided parameters

    """
    example_usage = """Example usage :
            run_cmd.py -customer ATT_NEO_LAB -type SAOS vyatta -getter sh_ver
            run_cmd.py -customer ATT_NEO_LAB -type vyatta -cmd show ip bgp summ"""

    options = argparse.ArgumentParser(description="\nRun command on various devices using nornir",
                                      epilog=example_usage)
    options.add_argument('-customer', metavar="CUSTOMER_NAME", help='Specify Customer NAME', nargs='?')
    options.add_argument('-type', choices=['SAOS', 'vyatta', 'DNFVI'], help='Device OS / vendors', nargs='+')
    group = options.add_mutually_exclusive_group(required=True)
    group.add_argument('-cmd', metavar="custom_command",
                       help='Specify Custom command for a single device type', nargs='+')
    group.add_argument('-getter', metavar="standard_command", choices=['sh_run', 'sh_ver'],
                       help='Specify command to be run on all device types', nargs='+')

    args = options.parse_args()

    if args.cmd:
        args.cmd = ' '.join(args.cmd)
    if not (args.customer or args.type):
        options.error('At least one argument required')
    if args.cmd and len(args.type) > 1:
        options.error('Custom command can only be run on a single device type')

    return args


def get_command(task, opt):
    """
    Custom nornir task : run getter for various or custom command for single dev type and write to file

    """

    if opt.cmd is None:
        command = cmd[task.host.groups[0]][opt.getter[0]]
        filename = f'{task.host}_{opt.getter[0] }.txt'
    else:
        command = opt.cmd
        filename = f'{task.host}_custom.txt'

    print(f' For device {task.host} run : {command}')

    if task.host.groups[0] == 'DNFVI':
        dev = Dnfvi(task.host.hostname, task.host.username, task.host.password)
        try:
            res = dev._send_cmd(command)
        except:
            res = f"Exception {sys.exc_info()} occurred"
    else:
        a = task.run(name="Run command",
                     task=networking.netmiko_send_command,
                     command_string=command)
        res = a.result

    print(f' Writing result to file : results/{filename}')
    task.run(name="Write result to file", task=write_file, filename=f"results/{filename}", content=res)

    return


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

    devices = InitNornir(core={"num_workers": 10},
                         inventory={"plugin": "custom_inventory.BpoInventory",
                                    "options": {
                                        "bpo_ip": bpo["ip"],
                                        "bpo_user": bpo["user"],
                                        "bpo_pass": bpo["pass"],
                                        "bpo_tenant": bpo["tenant"],
                                    }
                                    })
    filt_dev = devices.filter(F(groups__any=opt.type))

    for platf in opt.type:
        try:
            devices.inventory.groups[platf].username = input(f'Enter {platf} username : ')
            devices.inventory.groups[platf].password = getpass.getpass(f'Enter {platf} user password: ')
        except (TypeError, KeyError):
            print("Error populating credentials, verify if adequate groups are present in custom inventory")

    print("calling task ...")
    filt_dev.run(name="Get command", task=get_command, opt=opt)
    print("DONE.")

    return


if __name__ == "__main__":
    main()
