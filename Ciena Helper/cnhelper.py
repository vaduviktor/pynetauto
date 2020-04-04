import time
from netmiko import ConnectHandler, redispatch
import requests
import json
import sys
from ncclient import manager
import xmltodict
"""
Helper module for saos, Blue Planet, dnfvi 

"""


class Saos:
    # for netmiko
    _dev = {
        'device_type': 'ciena_saos',
        'ip': '',
        'username': 'diag',
        'password': 'ciena123',
        'port': 22
    }

    # wip
    xpath = {
        "port_status": '',
        "xcvr_status": '',
        "module_shwo": '',
        "config": '',
        "interfaces": '//interfaces/interface'
    }

    _net_connect = ''
    _netconf_conn = ''

    def __init__(self, dev_ip, username, password, method="ssh"):
        self._dev["ip"] = dev_ip
        self._dev["username"] = username
        self._dev["password"] = password
        self._method = method  # ssh or netconf
        if self._method == "ssh":
            self._connect_ssh()
        else:
            self._connect_netconf()

    def __del__(self):
        self.close()

    def close(self):
        try:
            if self._method == 'ssh':
                self._net_connect.disconnect()
                print('ssh session closed')
            else:
                self._netconf_conn.close_session()
                print('Netconf session closed')
        except:
            print("No ssh or netconf sessions established")
            print(f"Exception {sys.exc_info()} occured")
        return

    def _connect_netconf(self):
        try:
            self._netconf_conn = manager.connect(host=self._dev["ip"], username=self._dev["username"],
                                                 password=self._dev["password"], hostkey_verify=False, timeout=10)
        except:
            print(f"Exception {sys.exc_info()} occured")
        return

    def _netconf_get(self, xpath: str) -> dict:
        try:
            res = self._netconf_conn.get(filter=("xpath", f"{xpath}"))
            dict_res = xmltodict.parse(res.xml)
        except:
            dict_res = {}

        return dict_res

    def _connect_ssh(self):
        try:
            self._net_connect = ConnectHandler(**self._dev)
        except:
            print(f"Exception {sys.exc_info()} occured")
        return

    def _send_cmd(self, cmd: str) -> str:
        try:
            res = self._net_connect.send_command(cmd)
        except:
            res = f"Exception {sys.exc_info()[0]} occured"

        return res

    def int_status(self):
        res = self._send_cmd("port show")
        return res

    def int_stats(self, int_num):
        res = self._send_cmd(f'port show port {int_num} statistics')
        return res

    def int_sfp_status(self):
        res = self._send_cmd("port xcvr show")
        return res

    def int_sfp_detail(self, int_num):
        res = self._send_cmd(f"port xcvr show port {int_num}")
        return res

    def module_status(self):
        res = self._send_cmd("module show module NFV")
        return res

    def get_config(self) -> str:
        res = self._send_cmd("config show brief")
        return res


class Dnfvi:
    api_calls = {
        "Token": "/rest/auth/login",
        "License_status": "/rest/license_mgmt/status/formatted",
        "SFFS": "/rest/sffs/show",
        "VNFs": "/rest/vnf/show",
        "Files": "/rest/vnf/file_mgmt/show/formatted"
    }

    xpath = {
        "SFF": '//sfs/sf',
        'SF': '//sffs/sff',
        "nfvi": '/nfvi/nfvi-state',
        "sw_state": '/software-state',
        "system_state": '/system-state',
        "licence_state": '/license-management-state'
    }

    # for netmiko
    _dev = {
        'device_type': 'terminal_server',
        'ip': '',
        'username': 'diag',
        'password': 'asdf',
        'port': 830
    }

    _connection = ''
    _conn_netconf = ''
    _host = False
    _auth_token = ''
    _method = 'ssh'
    _tmp = ''

    def __init__(self, dev_ip, username, password, **kwargs):
        """
        When initialising you have to specify ip, username, pass and if you want this to be ssh to host( host=True)
        or REST call( method = REST )

        examples :
        REST : dev.Dnfvi(ip, username, pass, method='REST')
        cn_core_host : dev.Dnfvi(ip, username, pass, host=True)
        ui/valcli : dev.Dnfvi(ip, username, pass)
        NETCONF : dev.Dnfvi(ip, username, pass, method='netconf')


        """
        self._dev["ip"] = dev_ip
        self._dev["username"] = username
        self._dev["password"] = password
        if kwargs:
            for key, value in kwargs.items():
                if key == "method":
                    self._method = value
                if key == 'host':
                    self._host = value
        if self._method == 'REST':
            self._auth_token = self._get_auth_token()
            self._host = False
        elif self._method == "netconf":
            self._connect_netconf()
            self._host = False
        else:
            try:
                self._connect(self._host)
            except:
                print("Error connecting")

    def __del__(self):
        self.close()

    def close(self):
        try:
            if self._method == 'ssh':
                self._connection.disconnect()
                print('ssh session closed')
            else:
                self._conn_netconf.close_session()
                print('Netconf session closed')
        except:
            print("No ssh or netconf sessions established")
            print(f"Exception {sys.exc_info()} occured")
        return

    def _send_cmd(self, cmd):  # wip
        if self._host:
            res = "ERROR, object initialized as host"
        elif self._dev["device_type"] == "linux":
            self._connection.send_command_timing("yp-shell")
            res = self._connection.send_command_timing(cmd)
        else:
            res = self._connection.send_command(cmd)
        return res

    def _connect_netconf(self):
        try:
            self._conn_netconf = manager.connect(host=self._dev["ip"], username=self._dev["username"],
                                                 password=self._dev["password"], hostkey_verify=False, timeout=10)
        except:
            print(f"Exception {sys.exc_info()} occured")
        return

    def _netconf_get(self, xpath: str) -> dict:
        try:
            res = self._conn_netconf.get(filter=("xpath", f"{xpath}"))
            dict_res = xmltodict.parse(res.xml)
        except:
            dict_res = {}

        return dict_res

    def _connect(self, host=False) -> None:
        """
        Initially connect as type terminal_server and based on prompt determine if its 10x or 18x system

        10x gets you to valcli shell while 18x gets you to UI linux container shell ( for user diag ( non-netconf))

        if host True "drill down" through shells, expect style, to cn_core_host and then set netmiko session as linux

        """

        try:
            self._connection = ConnectHandler(**self._dev)
        except:
            print(f"Exception {sys.exc_info()} occured")

        self._connection.write_channel("\r\n")
        time.sleep(1)
        self._connection.write_channel("\r\n")
        time.sleep(1)
        output = self._connection.read_channel()
        print("Looking for prompt")
        if ">" in output:
            print("Found 10x ...\r\n")
            if not host:
                # redispatch to ciena_saos and disabling pager
                redispatch(self._connection, device_type='ciena_saos')
                print("disabling pager on 10x cli")
                self._connection.send_command("set session more off")
                print(self._connection.find_prompt())
                self._tmp = 'ciena_saos'
            else:
                self._connection.write_channel("diag shell\r\n")
                time.sleep(1)
                # output = net_connect.read_channel()
                self._connection.write_channel("ssh cn_core_host\r\n")
                time.sleep(1)
        else:
            print("Found 18x ... in ui\n")
            if not host:
                redispatch(self._connection, device_type='linux')
                print(self._connection.find_prompt())
                self._tmp = 'linux'
            else:
                self._connection.write_channel("ssh cn_core_host\r\n")
                time.sleep(1)

        if host:
            max_loops = 5
            i = 1
            while i <= max_loops:
                output = self._connection.read_channel()
                # Search for password pattern / send password
                if 'yes/no' in output:
                    self._connection.write_channel('yes\r\n')
                    time.sleep(.5)
                elif "password" in output:
                    self._connection.write_channel(self._dev["password"] + '\r\n')
                    time.sleep(.5)
                    output = self._connection.read_channel()
                    # Did we successfully login
                    if 'NFV-FRU' in output:
                        # print(output)
                        break
                self._connection.write_channel('\r\n')
                time.sleep(.5)
                i += 1
            print("Doing redispatch to dev type linux")
            redispatch(self._connection, device_type='linux')
            self._tmp = 'linux'
            print(self._connection.find_prompt())

        return

    def get_nfvi(self):
        if self._host:
            res = "ERROR, object initialized as host"
        elif self._method == "REST":
            res = "Not implemented yet"
        elif self._method == "netconf":
            res = self._netconf_get(self.xpath["nfvi"])
        elif self._tmp == "linux":
            self._connection.send_command_timing("yp-shell")
            res = self._connection.send_command_timing("sget /nfvi")
            self._connection.send_command_timing("quit")
        else:
            res = self._connection.send_command('show nfvi')
        return res

    def get_sfs(self):
        if self._host:
            res = "ERROR, object initialized as host"
        elif self._method == "REST":
            res = self.rest_apicall("GET", self.api_calls["VNFs"])
        elif self._method == "netconf":
            res = self._netconf_get(self.xpath["SFS"])
        elif self._tmp == "linux":
            self._connection.send_command_timing("yp-shell")
            res = self._connection.send_command_timing("sget /sfs")
            self._connection.send_command_timing("quit")
        else:
            res = self._connection.send_command("show nfvi sfs")
        return res

    def get_sffs(self):
        if self._host:
            res = "ERROR, object initialized as host"
        elif self._method == "REST":
            res = self.rest_apicall("GET", self.api_calls["SFFS"])
        elif self._method == "netconf":
            res = self._netconf_get(self.xpath["SFFS"])
        elif self._tmp == "linux":
            self._connection.send_command_timing("yp-shell")
            res = self._connection.send_command_timing("sget /sffs")
            self._connection.send_command_timing("quit")
        else:
            res = self._connection.send_command("show sffs")
        return res

    def host_cnfp_int_stat(self):
        if not self._host:
            return "ERROR, not initialized as host"
        cmd = 'sudo docker exec -it cn_cnfp_1 cnfp-dbg getif 0 all'
        return self._connection.send_command(cmd)

    def host_cnfp_int_reset(self):
        if not self._host:
            return "ERROR, not initialized as host"
        cmd = 'sudo docker exec -it cn_cnfp_1 cnfp-dbg getif 0 all reset'
        return self._connection.send_command(cmd)

    def rest_apicall(self, method: str, api_call: str, *args, **kwargs) -> dict:
        """
                Generl API call FN

                :param method: GET, POST, PUT, PATCH, DELETE
                :param api_call: api_calls[CALL] or str
                :param args: arguments for api call
                :param kwargs: filters for api call .. or custom data and headers for http request
                :return: res dict {"status_code", "Result"}
        """

        filters = ''
        if not args:
            callapi = api_call
        else:
            callapi = api_call.format(args[0])

        auth = f'Bearer {self._auth_token}'
        data = ''
        headers = {'accept': "application/json", 'Authorization': auth, 'Content-Type': 'application/json'}

        if kwargs:
            filters = "?"
            nextarg = ''
            for key, value in kwargs.items():
                if key == 'data':
                    data = json.dumps(value)
                elif key == 'headers':
                    headers = value
                else:
                    filters = filters + nextarg + f"{key}={value}"
                    nextarg = '&'

        urlcore = f'https://{self._dev["ip"]}'
        url = urlcore + callapi + filters

        try:
            req = requests.request(method, url, data=data, headers=headers, verify=False)
            res = {
                "status_code": req.status_code,
                "Result": req.json()
            }
        except:
            print(f"Exception {sys.exc_info()[0]} occured")
            res = {"status_code": sys.exc_info(), "Result": 'None'}

        return res

    def _get_auth_token(self) -> str:
        """
        Get auth token
        """
        headers = {'accept': "application/json", 'Content-Type': "application/x-www-form-urlencoded"}
        data = {"username": self._dev["username"], "password": self._dev["password"]}
        url = f'https://{self._dev["ip"]}{self.api_calls["Token"]}'

        try:
            req = requests.request('POST', url, data=data, headers=headers, verify=False)
            res = {
                "status_code": req.status_code,
                "Result": req.json()
            }
        except:
            print(f"Exception {sys.exc_info()[0]} occured")
            res = {"status_code": sys.exc_info(), "Result": 'None'}

        try:
            tok = res["Result"]["token"]
            print(tok)
        except (TypeError, KeyError):
            tok = 'None'
            print(res)

        return tok


class Bpo:
    api_calls = {
        "Resource_Operation": "/bpocore/market/api/v1/resources/{}/operations",
        "Single_Resource": "/bpocore/market/api/v1/resources/{}",
        "Resources": "/bpocore/market/api/v1/resources",
        "Resource Dependents": "/bpocore/market/api/v1/resources/{}/dependents",
        "Domains": "/bpocore/market/api/v1/domains",
        "Products_in_Domain": "/bpocore/market/api/v1/domains/{}/products",
        "Token": "/tron/api/v1/tokens",
        "Products": "/bpocore/market/api/v1/products"
    }

    _bpo = {
        "bpo_ip": '',
        "bpo_user": '',
        "bpo_pass": '',
        "bpo_tenant": '',
        "bpo_auth_token": ''
    }

    def __init__(self, bpo_ip, username, password, tenant):
        self._bpo["bpo_ip"] = bpo_ip
        self._bpo["bpo_user"] = username
        self._bpo["bpo_pass"] = password
        self._bpo["bpo_tenant"] = tenant
        self._bpo["bpo_auth_token"] = self.__get_auth_token()

    def apicall(self, method: str, api_call: str, *args, **kwargs) -> dict:
        """
        Generl API call FN

        :param method: GET, POST, PUT, PATCH, DELETE
        :param api_call: api_calls[CALL] or str
        :param args: arguments for api call
        :param kwargs: filters for api call .. or custom data and headers for http request
        :return: res dict {"status_code", "Result"}
        """

        filters = ''
        if not args:
            callapi = api_call
        else:
            callapi = api_call.format(args[0])

        auth = f'Bearer {self._bpo["bpo_auth_token"]}'
        data = ''
        headers = {'accept': "application/json", 'Authorization': auth, 'Content-Type': 'application/json'}

        if kwargs:
            filters = "?"
            nextarg = ''
            for key, value in kwargs.items():
                if key == 'data':
                    data = json.dumps(value)
                elif key == 'headers':
                    headers = value
                else:
                    filters = filters + nextarg + f"{key}={value}"
                    nextarg = '&'

        urlcore = f'https://{self._bpo["bpo_ip"]}'
        url = urlcore + callapi + filters

        try:
            req = requests.request(method, url, data=data, headers=headers, verify=False)
            res = {
                "status_code": req.status_code,
                "Result": req.json()
            }
        except:
            print(f"Exception {sys.exc_info()[0]} occured")
            res = {"status_code": sys.exc_info(), "Result": 'None'}

        return res

    def __get_auth_token(self) -> str:
        """
        Get auth token
        """
        headers = {'accept': "application/json", 'Content-Type': "application/json"}
        data = {"username": self._bpo["bpo_user"], "password": self._bpo["bpo_pass"],
                "tenant_context": self._bpo["bpo_tenant"]}
        token = self.apicall('POST', self.api_calls["Token"], data=data, headers=headers)
        try:
            tok = token["Result"]["token"]
            print(tok)
        except (TypeError, KeyError):
            tok = 'None'
            print(token)

        return tok

    def get_device_list(self) -> list:
        """
        Get dnfvi device list

        :return : devlist[0] if i == 1 else devlist <---- if tenant = master it might have multiple dnfvi domains

        """
        devlist = []
        i = 0
        dnfvi_domain = self.get_domains(q=f'domainType:urn:ciena:bp:domain:dnfvi')["Result"]
        # multiple domains found if tenant master ... for other tenants its only single iter
        for item in dnfvi_domain["items"]:
            domain_id = item["id"]
            dnfvi_dev_prod = self.get_products_in_domain(domain_id, q='title:dnfvi Device')["Result"]
            # this should return only one result in list but iter just in case
            for prod in dnfvi_dev_prod["items"]:
                dnfvi_devices = self.get_resources(productId=prod["id"])["Result"]
                devlist.append(dnfvi_devices["items"])
                i += 1

        return devlist[0] if i == 1 else devlist

    def get_vnf_list(self) -> list:
        """
        Get list of all VNFs
        """
        vnflist = []
        dnfvi_domain = self.get_domains(q=f'domainType:urn:ciena:bp:domain:dnfvi')["Result"]
        i = 0
        # multiple domains found if tenant master ... for other tenants its only single iter
        for item in dnfvi_domain["items"]:
            domain_id = item["id"]
            dnfvi_dev_prod = self.get_products_in_domain(domain_id, q='title:dnfvi VNF')["Result"]
            # this should return only one result in list but iter just in case
            for prod in dnfvi_dev_prod["items"]:
                dnfvi_devices = self.get_resources(productId=prod["id"])["Result"]
                vnflist.append(dnfvi_devices["items"].copy())
                i += 1

        return vnflist[0] if i == 1 else vnflist

    def get_domains(self, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Domains"], **filters)

    def get_products_in_domain(self, arg: str, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Products_in_Domain"], arg, **filters)

    def get_products(self, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Products"], **filters)

    def get_resources(self, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Resources"], **filters)

    def get_specific_resource(self, arg: str, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Single_Resource"], arg, **filters)

    def get_resource_operation(self, arg: str, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Resource_Operation"], arg, **filters)

    def get_resource_dependents(self, arg: str, **filters) -> dict:
        return self.apicall('GET', self.api_calls["Resource Dependents"], arg, **filters)
