import requests
import json
import warnings
import sys

"""
BPO API calls

"""


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

    __bpo = {
        "bpo_ip": '',
        "bpo_user": '',
        "bpo_pass": '',
        "bpo_tenant": '',
        "bpo_auth_token": ''
    }

    def __init__(self, bpo_ip, username, password, tenant):
        self.__bpo["bpo_ip"] = bpo_ip
        self.__bpo["bpo_user"] = username
        self.__bpo["bpo_pass"] = password
        self.__bpo["bpo_tenant"] = tenant
        self.__bpo["bpo_auth_token"] = self.__get_auth_token__()

    def __apicall__(self, method: str, api_call: str, *args, **kwargs) -> dict:
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

        auth = f'Bearer {self.__bpo["bpo_auth_token"]}'
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

        urlcore = f'https://{self.__bpo["bpo_ip"]}'
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

    def __get_auth_token__(self) -> str:
        """
        Get auth token
        """
        headers = {'accept': "application/json", 'Content-Type': "application/json"}
        data = {"username": self.__bpo["bpo_user"], "password": self.__bpo["bpo_pass"],
                "tenant_context": self.__bpo["bpo_tenant"]}
        token = self.__apicall__('POST', self.api_calls["Token"], data=data, headers=headers)
        try:
            tok = token["Result"]["token"]
            print(tok)
        except (TypeError, KeyError):
            tok = 'None'
            print(token)

        return tok

    def get_domains(self, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Domains"], **filters)

    def get_products_in_domain(self, arg: str, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Products_in_Domain"], arg, **filters)

    def get_products(self, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Products"], **filters)

    def get_resources(self, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Resources"], **filters)

    def get_specific_resource(self, arg: str, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Single_Resource"], arg, **filters)

    def get_resource_operation(self, arg: str, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Resource_Operation"], arg, **filters)

    def get_resource_dependents(self, arg: str, **filters) -> dict:
        return self.__apicall__('GET', self.api_calls["Resource Dependents"], arg, **filters)




