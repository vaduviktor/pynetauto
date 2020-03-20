import requests
import json
from openpyxl import Workbook
import argparse
import getpass
import warnings
import time
import sys

"""
Connect to BPO and get VNFs per device and their flavours


"""

bpo_details = {
    "bpo_ip": '',
    "bpo_user": '',
    "bpo_pass": '',
    "bpo_tenant": '',
    "bpo_auth_token": ''
}

api_calls = {
    "Resource_Operation": "/bpocore/market/api/v1/resources/{}/operations",
    "Single_Resource": "/bpocore/market/api/v1/resources/{}",
    "Resources": "/bpocore/market/api/v1/resources",
    "Resource Dependents": "/bpocore/market/api/v1/resources/{}/dependents",
    "Domains": "/bpocore/market/api/v1/domains",
    "Products_in_Domain": "/bpocore/market/api/v1/domains/{}/products"
}


def get_call(bpo, api_call, *args, **kwargs):
    """
    General api call fn.

    :param bpo: bpo_details
    :param api_call: api_calls["CALL"]
    :param args: argument for api call ... resource ID or domain ID ( depending on call )
    :param kwargs: additional filters
    :return: response dict
    """

    auth = f'Bearer {bpo["bpo_auth_token"]}'
    filters = ''

    # format api call based on passed args ( only one used [0] )
    if not args:
        callapi = api_call
    else:
        callapi = api_call.format(args[0])

    # format filters based on passed kwargs ( dict )
    if kwargs:
        filters = "?"
        nextarg = ''
        for key, value in kwargs.items():
            filters = filters + nextarg + f"{key}={value}"
            nextarg = '&'

    urlcore = f'https://{bpo["bpo_ip"]}'
    headers = {'accept': "application/json", 'Authorization': auth}
    url = urlcore + callapi + filters
    print(f"URL : {url}")  # dbg, verify

    try:
        req = requests.request("GET", url, headers=headers, verify=False)
        if req.status_code == 200:
            result = req.json()
        else:
            print("Some other error :) ")
            print(req.status_code)
            result = ''
    except:
        print(f"Exception {sys.exc_info()[0]} occured")
        result = ''

    return result


def get_auth_token(bpo):
    """
    Get auth token from BPO

    :return token:
    """
    token = None

    url = 'https://' + bpo["bpo_ip"] + '/tron/api/v1/tokens'
    headers = {'accept': "application/json", 'Content-Type': "application/x-www-form-urlencoded"}
    data = {
        "username": bpo["bpo_user"],
        "password": bpo["bpo_pass"],
        "tenant_context": bpo["bpo_tenant"]
    }

    req = requests.request("POST", url, data=data, headers=headers, verify=False)

    if req.status_code == 401:
        print("Error: UNAUTHORIZED")
    elif req.status_code == 201:
        token = req.json()["token"]
        print("TOKEN : {}".format(token))
    else:
        print("TOKEN : Some other error :) ")
        print(req.status_code)

    return token


def find_vnf_flavour(name, cpu, mem):
    """
    Load VNF_Flavours_TABLE json and cross compare it to input parameters in order to get VNF flavour

    """
    # load VNF_flavour json
    flv_data = json.loads(open("FLV2.json", "r").read())
    # depending on vnf name assign vnf model matrix
    if "vce" in name:
        vend = 1
    elif "vrouter" in name:
        vend = 0
    elif "pa" in name:
        vend = 2
    else:
        return 'Unknown'  # return Unknown if no VNF found in name

    model = 'Unknown'
    for item in flv_data["Vendors"][vend]["VNF_models"]:
        if cpu == item["vCPU"] and (item["Memory"] - 1 < (mem / 1024) < item["Memory"] + 1):
            model = item["model"]

    return model


def get_vnfs(devices, domain_id):
    """
    Go through DNFVI devices, get VNFs and its flavour per device

    :param devices:
    :param domain_id:
    :return: Device VNF list
    """
    # get VNFs
    dnfvi_vnf_prod = get_call(bpo_details, api_calls["Products_in_Domain"],
                              domain_id, q='title:dnfvi VNF')
    dnfvi_vnf_prod_id = dnfvi_vnf_prod["items"][0]["id"]

    dev_vnf_list = []

    # go through reachable devices and get vnfs
    for item in devices["items"]:
        time.sleep(3)  # slow down request rate
        if not item["properties"]["communicationState"] == "AVAILABLE":
            continue
        devs = {"Device IP": item["properties"]["connection"]["hostname"],
                "Device hostname": item["label"],
                "Device desc": item["properties"]["city"],
                "Device ID": item["id"],
                "Device status": item["properties"]["communicationState"],
                "VNFs": []
                }

        # get VNFs for specific deice
        dev_vnfs = get_call(bpo_details, api_calls["Resource Dependents"], item["id"], productId=dnfvi_vnf_prod_id)

        for vnf in dev_vnfs["items"]:
            vnfs = {
                "VNF_name": vnf["label"],
                "VNF_id": vnf["id"],
                "VNF_cpu_num": vnf["properties"]["status"]["cpuUsed"],
                "VNF_memory": vnf["properties"]["status"]["memAllocated"],
                "VNF_flavour": 'Unknown',
                "VNF_flv_initial": 'Unknown'
            }
            flavour = find_vnf_flavour(vnfs["VNF_name"], vnfs["VNF_cpu_num"], vnfs["VNF_memory"])
            vnfs["VNF_flavour"] = flavour
            devs["VNFs"].append(vnfs.copy())
        dev_vnf_list.append(devs.copy())

    return dev_vnf_list


def cross_compare(dev_vnf_list):
    """
    Get all instantiations and cross compare with device/vnf list to get calculated vs instantiated flavours

    """

    ra_domain = get_call(bpo_details, api_calls["Domains"], q=f'domainType:WorkflowManager')
    ns_info_prod = get_call(bpo_details, api_calls["Products_in_Domain"],
                            ra_domain["items"][0]["id"], q='title:Ns Info')
    instantiations = get_call(bpo_details, api_calls["Resources"], productId=ns_info_prod["items"][0]["id"])

    # go through instantiations
    for instance in instantiations["items"]:
        if not instance["properties"]["instantiationState"] == "INSTANTIATED":
            continue
        # get operation for every instantiation
        time.sleep(3)  # slow down request rate
        operations = get_call(bpo_details, api_calls["Resource_Operation"], instance["id"], q='interface:instantiateNs')

        # skip iteration if unable to assign required vim/params data ... operations returned empty items list
        try:
            vim = operations["items"][0]["inputs"]["locationConstraints"][0]["locationConstraints"]["vims"][0]
            params = operations["items"][0]["inputs"]["additionalParamsForVNF"]
        except:
            continue
        # cross compare with device list
        for device in dev_vnf_list:
            if device["Device ID"] == vim:
                # cross compare with device vnfs
                for vnf in device["VNFs"]:
                    for param in params:
                        levelid = param["additionalParam"]["keyValuePairs"][0]["value"]["levelId"]
                        if vnf["VNF_name"].split("_", 2)[1] in levelid:
                            vnf["VNF_flv_initial"] = levelid
                        elif vnf["VNF_name"].split("_", 2)[1] == "vrouter" and "vyatta" in levelid:
                            vnf["VNF_flv_initial"] = levelid

    return dev_vnf_list


def excel_out(dev_vnf_list):
    """
    Create Excel report

    """
    wb = Workbook()
    sheet = wb.active
    sheet.title = "RESULTS"

    sheet['B2'] = "Sitename"
    sheet['C2'] = "Device label"
    sheet['D2'] = "Device IP"
    sheet['E2'] = "VNF name"
    sheet['F2'] = "VNF flavour calculated"
    sheet['G2'] = "VNF flavour instantiated"

    i = 3
    for item in dev_vnf_list:
        for vnf in item["VNFs"]:
            sheet['B{}'.format(i)] = item["Device desc"]
            sheet['C{}'.format(i)] = item["Device hostname"]
            sheet['D{}'.format(i)] = item["Device IP"]
            sheet['E{}'.format(i)] = vnf["VNF_name"].split("_", 2)[1]
            sheet['F{}'.format(i)] = vnf["VNF_flavour"]
            sheet['G{}'.format(i)] = vnf["VNF_flv_initial"]
            i += 1

    sheet.auto_filter.ref = "B{}:G{}".format(2, i - 1)
    wb.save(filename=f'REPORT_{bpo_details["bpo_tenant"]}.xlsx')

    return


def check_options():
    """
    Check provided arguments

    :return args:
    """
    example_usage = "EXAMPLE :  GetVNFs.py -bpo 10.10.20.25:8443 -tenant CUSTOMER"

    options = argparse.ArgumentParser(description="Connect BPO and get all VNFs and its flavours .. output RESULT.xlsm",
                                      epilog=example_usage)
    options.add_argument('-bpo', required=True, help='BPO IP', nargs="?")
    options.add_argument('-tenant', required=True, help='BPO Tenant / Customer', nargs="?")

    args = options.parse_args()

    return args


def main():
    # suppress self-signed cert HTTPS warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    # Check options and populate bpo details
    args = check_options()
    bpo_details["bpo_user"] = input("Enter BPO username: ")
    bpo_details["bpo_pass"] = getpass.getpass("Enter BPO user password: ")
    bpo_details["bpo_ip"] = args.bpo
    bpo_details["bpo_tenant"] = args.tenant
    bpo_details["bpo_auth_token"] = get_auth_token(bpo_details)

    # get domain, products, device resources and vnfs
    dnfvi_domain = get_call(bpo_details, api_calls["Domains"], q=f'domainType:urn:ciena:bp:domain:dnfvi')
    dnfvi_dev_prod = get_call(bpo_details, api_calls["Products_in_Domain"],
                              dnfvi_domain["items"][0]["id"], q='title:dnfvi Device')
    dnfvi_devices = get_call(bpo_details, api_calls["Resources"], productId=dnfvi_dev_prod["items"][0]["id"])

    vnf_list = get_vnfs(dnfvi_devices, dnfvi_domain["items"][0]["id"])
    excel_out(cross_compare(vnf_list))

    return


if __name__ == "__main__":
    main()
