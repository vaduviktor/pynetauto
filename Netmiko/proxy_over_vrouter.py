from __future__ import print_function, unicode_literals
from netmiko import ConnectHandler, redispatch
import logging
"""
Connect to SAOS SW using vyos as a proxy
"""

def main():

    dev = {
        'device_type': 'vyos',
        'ip': '172.17.143.1',
        'username': 'vyos',
        'password': 'vyos',
        'port': 22
    }

    saos = {"ip": "172.17.143.3",
            "user": "user",
            "passwd": "pass"
            }

    # logger for dbg
    # logging.basicConfig(filename="test.log", level=logging.DEBUG)
    # logger = logging.getLogger("netmiko")
    
    # connect to vrouter
    net_connect = ConnectHandler(**dev)
    print(net_connect.find_prompt())

    # jump to saos from vrouter ... MGMT vrf is device specific config
    cmd = f"ssh {saos['user']}@{saos['ip']} routing-instance MGMT"
    try:
        output = net_connect.send_command_expect(cmd, expect_string="Password")
        print(output)
    except:
        try:
            net_connect.send_command_expect(cmd, expect_string="(yes/no)?")
            output = net_connect.send_command_expect('yes', expect_string="Password")
            print(output)
        except:
            print("Error connecting to SAOS")
            net_connect.disconnect()
            return

    output = net_connect.send_command_timing(saos['passwd'])
    print(output)

    print("Doing redispatch to dev type ciena_saos")
    try:
        redispatch(net_connect, device_type='ciena_saos')
    except:
        print("ERROR redispatching, SAOS prompt not found ... verify login credentials")
        net_connect.disconnect()
        return

    net_connect.set_base_prompt(pri_prompt_terminator=">", alt_prompt_terminator="*>")

    cmd = "port show status"
    print("sending command")
    # import ipdb; ipdb.set_trace() # dbg
    res = net_connect.send_command(cmd, auto_find_prompt=False)
    print(res)

    net_connect.disconnect()
    return


if __name__ == "__main__":
    main()

