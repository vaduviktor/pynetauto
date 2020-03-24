from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.tasks import networking
from nornir.plugins.tasks.files import write_file
import argparse
import getpass

"""
Run command on various devices using nornir and write result to file

Example usage :
            getter.py -customer NCR_LAB -type cisco vyatta -getter sh_ver
            getter.py -customer NCR_LAB -type cisco -cmd show crypto isa sa

"""

cmd = {
    "SAOS": {"sh_run": 'config show brief',
             "sh_ver": 'system show version'},
    "vyatta": {"sh_run": 'show configuration commands',
               "sh_ver": 'show version'},
    "cisco": {"sh_run": 'show run',
              "sh_ver": 'show version'},
    "juniper": {"sh_run": 'show configuration commands',
                "sh_ver": 'show version'}
}


def check_options():
    """
    Check provided parameters

    """
    example_usage = """Example usage :
            getter.py -customer NCR_LAB -type cisco vyatta -getter sh_ver
            getter.py -customer NCR_LAB -type cisco -cmd show inventory"""

    options = argparse.ArgumentParser(description="\nRun command on various devices using nornir",
                                      epilog=example_usage)
    options.add_argument('-customer', metavar="CUSTOMER_NAME", help='Specify Customer NAME', nargs='?')
    options.add_argument('-type', choices=['SAOS', 'vyatta', 'cisco', 'juniper'], help='Device OS / vendors', nargs='+')
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
    if task.host.groups == "cisco":
        en = True
    else:
        en = False

    print(f' For device {task.host} run : {cmd[task.host.groups[0]][opt.getter] if not opt.cmd else opt.cmd}')

    a = task.run(name="Run command",
                 task=networking.netmiko_send_command,
                 command_string=cmd[task.host.groups[0]][opt.getter] if not opt.cmd else opt.cmd,
                 enable=en)
    print(f' Writing result for : {task.host}')
    custom = 'custom'
    filename = f'{task.host}_{cmd[task.host.groups[0]][opt.getter] if not opt.cmd else custom}.txt'
    task.run(name="Write result to file", task=write_file, filename=f"results/{filename}", content=a.result)

    return


def main():
    # check arguments
    opt = check_options()

    devices = InitNornir(config_file="config.yaml")
    filt_dev = devices.filter(F(groups__any=opt.type))  # to test : & or |  F(customer=opt.customer)

    # credentials input ... assumes you have adequate groups in groups.yaml file
    for type in opt.type:
        try:
            devices.inventory.groups[type].username = input(f'Enter {type} username : ')
            devices.inventory.groups[type].password = getpass.getpass(f'Enter {type} user password: ')
            if type == "cisco":
                devices.inventory.groups[type].connection_options["netmiko"].extras["secret"] = getpass.getpass(f'Enter {type} enable password: ')
        except (TypeError, KeyError):
            print("Error populating credentials, verify if adequate groups are in your groups.yaml file")

    print("calling task ...")
    filt_dev.run(name="Get command", task=get_command, opt=opt)
    print("DONE.")

    return


if __name__ == "__main__":
    main()
