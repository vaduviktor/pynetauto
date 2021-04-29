from nornir.core.deserializer.inventory import Inventory
from cnhelper import Bpo
import ipaddress


def get_devices_bpo(bpo) -> dict:
    """
    Get device list from BPO and transform it to Nornir inventory host dict

    """
    dev_dict = {}
    dev_platf = ["vyatta", "DNFVI", "SAOS"]

    # get device list from bpo and go through them
    for item in bpo.get_device_list():
        if item:  # <- can be an empty list in some cases with master tenant, don't care for exception
            if not item["properties"]["communicationState"] == "AVAILABLE":
                continue
        else:
            continue

        # follow a unique addressing per device : vyatta 1st, dnfvi 2nd and saos 3rd, BPO keeps track of dnfvi only
        a = 0
        start_ip = ipaddress.ip_address(item["properties"]["connection"]["hostname"]) - 1
        for platf in dev_platf:
            ip_addr = ipaddress.ip_address(start_ip) + a
            saos = ipaddress.ip_address(start_ip) + 2

            # add/update hosts dict
            dev_dict.update({
                f'{item["label"]}-{platf}': {
                    "hostname": str(ip_addr),
                    "groups": [platf],
                    "data": {
                        "customer": bpo._bpo["bpo_tenant"],
                        "saos_IP": str(saos) if a == 0 else ''
                    }
                }
            })
            a += 1

    return dev_dict


class BpoInventory(Inventory):
    def __init__(self, **kwargs):
        a = Bpo(kwargs["bpo_ip"], kwargs["bpo_user"], kwargs["bpo_pass"], kwargs["bpo_tenant"])
        hosts = get_devices_bpo(a)
        groups = {
            "vyatta": {
                "username": "vyatta",
                "password": '',
                "platform": 'vyos',
                "connection_options": {
                    "netmiko": {
                        "extras": {
                            "timeout": 3,
                            "global_delay_factor": 3
                        }
                    }
                },
                "data": {
                    "type": "network_device"
                }
            },
            "SAOS": {
                "username": "su",
                "password": '',
                "platform": 'ciena_saos',
                "connection_options": {
                    "netmiko": {
                        "extras": {
                            "timeout": 3,
                            "global_delay_factor": 3
                        }
                    }
                },
                "data": {
                    "type": "network_device"
                }
            },
            "DNFVI": {
                "username": "user",
                "password": '',
                "platform": 'linux',
                "port": 830,
                "connection_options": {
                    "netmiko": {
                        "extras": {
                            "timeout": 5,
                            "global_delay_factor": 3
                        }
                    }
                },
                "data": {
                    "type": "network_device"
                }
            }
        }
        defaults = {"data": {"location": "LAB", "language": "py"}}

        # passing the data to the parent class so the data is
        # transformed into actual Host/Group objects
        # and set default data for all hosts
        super().__init__(hosts=hosts, groups=groups, defaults=defaults, **kwargs)
