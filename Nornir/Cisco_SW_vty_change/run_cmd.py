from nornir import InitNornir
from nornir.plugins.tasks import networking
from nornir.plugins.functions.text import print_result
import getpass


def main_task(task):
    """
    Main Task

    """
    print(f'working on : {task.host.name}\n')
    task.run(name="PRE-CHECKS", task=pre_checks)

    if task.results[0].result:
        task.host.close_connections()
        return " Config already present"
    else:
        task.run(name="CONFIG CHANGE", task=change)

    task.run(name="VALIDATE", task=validate)

    # [2][1] .. 2 -> third task result in main task ... 1 -> second task result in validate task
    if task.results[2].result:
        task.run(name="SAVE CONFIG", task=networking.netmiko_save_config)
    else:
        task.host.close_connections()
        return 'Validation FAILED, some config added but none saved ... inspect manually ... or add more code :)'

    task.host.close_connections()

    return


def pre_checks(task):
    command = 'show run | s line vty 0 4'
    task.run(name="check vty 0 4", task=networking.netmiko_send_command, command_string=command, enable=True)
    command = 'show run | s line vty 5 15'
    task.run(name="check vty 5 15", task=networking.netmiko_send_command, command_string=command, enable=True)

    check = "exec-timeout 15"
    if check in str(task.results[0].result) and check in str(task.results[1].result):
        return True

    return False


def change(task):
    commands = ['line vty 0 4', 'exec-timeout 15']
    task.run(name="Change line vty 0 4 conf", task=networking.netmiko_send_config, config_commands=commands)
    commands = ['line vty 5 15', 'exec-timeout 15']
    task.run(name="Change line vty 5 15 conf", task=networking.netmiko_send_config, config_commands=commands)

    return


def validate(task):
    command = 'show run | s line vty 0 4'
    task.run(name="check vty 0 4", task=networking.netmiko_send_command, command_string=command, enable=True)
    command = 'show run | s line vty 5 15'
    task.run(name="check vty 5 15", task=networking.netmiko_send_command, command_string=command, enable=True)

    check = "exec-timeout 15"
    if check in str(task.results[0].result) and check in str(task.results[1].result):
        return True

    return False


def main():
    devices = InitNornir(core={"num_workers": 10},
                         inventory={"plugin": "custom_inventory.ExcelInventory"})

    devices.inventory.groups["ciscoSW"].username = input(f'Enter username : ')
    devices.inventory.groups["ciscoSW"].password = getpass.getpass(f'Enter password: ')

    en_pass = getpass.getpass(f'Enter enable password: ')
    devices.inventory.groups["ciscoSW"].connection_options["netmiko"].extras["secret"] = en_pass
    devices.inventory.groups["ciscoSW"].connection_options["napalm"].extras["optional_args"]["secret"] = en_pass

    result = devices.run(name="Main task", task=main_task)
    print_result(result)

    if result.failed:
        print(f'Failed hosts : {result.failed_hosts.keys()}')

    # import ipdb; ipdb.set_trace()

    return


if __name__ == "__main__":
    main()
