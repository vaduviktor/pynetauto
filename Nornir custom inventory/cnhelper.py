import time
from netmiko import ConnectHandler, redispatch
import requests
import json
import sys

"""
Helper module for SAOS, Blue Planet, dnfvi host and dnfvi ui ( 10x )

"""


class Saos:

    def __init__(self, method: str, dev_ip, username: str, password: str):
        self._ip = dev_ip
        self._username = username
        self._password = password
        self._method = method

    def __send_cmd(self):
        return

    def int_status(self):
        return

    def int_stats(self):
        return

    def int_sfp_status(self):
        return

    def int_sfp_detail(self):
        return

    def module_status(self):
        return

    def get_config(self):
        return


class Dnfvi:

    def __init__(self, method: str, dev_ip, username: str, password: str):
        self._ip = dev_ip
        self._username = username
        self._password = password
        self._method = method

    def __send_cmd(self):
        return

    def __redispatch_to_host(self):

        return

    def get_nfvi(self):
        return

    def get_sfs(self):
        return

    def get_sffs(self):
        return

    def host_cnfp_int_stat(self):
        return

    def host_cnfp_int_reset(self):
        return


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

