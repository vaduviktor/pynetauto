import meraki
import time
"""
Connect to dashboard, loop through LAB org networks, create new webhook on every network and update alerts
"""


def main():
    dashboard = meraki.DashboardAPI(
        api_key='1234',
        base_url='https://api.meraki.com/api/v0/',
        output_log=False,
        print_console=False
    )

    # Get all networks from organization ( in this case specific LAB org id )
    networks = dashboard.networks.getOrganizationNetworks('1234')

    for network in networks:
        net_id = network['id']
        net_name = network['name']

        # get network configured alerts
        net_alerts = dashboard.alert_settings.getNetworkAlertSettings(net_id)

        # create new webhook
        webhook_url = 'https://apibox.ml/meraki1234TEST'
        webhook_name = 'test'
        cred = {'sharedSecret': 'PASSWORD'}

        dashboard.http_servers.createNetworkHttpServer(net_id, webhook_name, webhook_url, **cred)

        # sleep for a second so we don't hit request limit
        time.sleep(1)

        # get all http servers and loop through them to acquire new webhook ID
        net_http_serv = dashboard.http_servers.getNetworkHttpServers(net_id)
        for server in net_http_serv:
            if server['name'] in webhook_name:
                webhook_id = server['id']

        # update alerts with new webhook id
        net_alerts['defaultDestinations']['httpServerIds'].append(webhook_id)
        dashboard.alert_settings.updateNetworkAlertSettings(net_id, **net_alerts)

    return


if __name__ == '__main__':
    main()