from netmiko import ConnectHandler
import sys


def main():
    dev = {
        'device_type': 'ciena_saos',
        'ip': sys.argv[1],
        'username': 'diag',
        'password': 'ciena123',
        'port': 830
    }

    net_connect = ConnectHandler(**dev)

    print(net_connect.find_prompt())

    # must disable pager so it doesnt break netmiko with ciena_saos connector
    cmd = "set session more off"
    net_connect.send_command(cmd)

    cmd = "show software"
    print(f'sending command {cmd} \n')
    res = net_connect.send_command(cmd)
    print(res)

    net_connect.disconnect()

    return


if __name__ == "__main__":
    main()
