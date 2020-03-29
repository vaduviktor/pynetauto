import time
from netmiko import ConnectHandler, redispatch
import sys

def main():
    dev = {
        'device_type': 'terminal_server',
        'ip': sys.argv[1],
        'username': 'diag',
        'password': 'asdf',
        'port': 830
    }

    cn_host_pass = 'qwerty'

    net_connect = ConnectHandler(**dev)

    net_connect.write_channel("\r\n")
    time.sleep(1)
    net_connect.write_channel("\r\n")
    time.sleep(1)
    output = net_connect.read_channel()
    print(output)

    # Login to end device from "terminal server"    ... ">" expected first if 10x ver or ui if 18x ver
    if ">" in output:
        print("Found 10x \n")
        net_connect.write_channel("diag shell\r\n")
        time.sleep(1)
        # output = net_connect.read_channel()
        net_connect.write_channel("ssh cn_core_host\r\n")
        time.sleep(1)
        # output = net_connect.read_channel()
        # print(output)
    else:
        print("Found 18x \n")
        net_connect.write_channel("ssh cn_core_host\r\n")
        time.sleep(1)
        # output = net_connect.read_channel()
        # print(output)

    # Manually handle the Username and Password
    max_loops = 5
    i = 1
    while i <= max_loops:
        output = net_connect.read_channel()
        print(output)

        # Search for password pattern / send password
        if 'yes/no' in output:
            net_connect.write_channel('yes\r\n')
            time.sleep(.5)
        elif "password" in output:
            net_connect.write_channel(cn_host_pass + '\r\n')
            time.sleep(.5)
            output = net_connect.read_channel()
            # Did we successfully login
            if 'NFV-FRU:' in output:
                print(output)
                break

        net_connect.write_channel('\r\n')
        time.sleep(.5)
        i += 1

    # Dynamically reset the class back to the proper Netmiko class
    print("Doing redispatch to dev type linux")
    redispatch(net_connect, device_type='linux')

    cmd = "sudo virsh list --all"
    # net_connect.send_command("sudo su")
    print("sending command")
    res = net_connect.send_command(cmd)
    print(res)

    net_connect.disconnect()

    return


if __name__ == "__main__":
    main()
