import cnhelper

# connect to ui ( 18x system )
a = cnhelper.Dnfvi('172.17.143.18', 'username', 'pass123', host=False)
print(a.get_sfs())
a.close()  # cleanup ( close session )
# del a  # cleanup ( close session )

# connect to 10x cli
b = cnhelper.Dnfvi('172.17.143.26', 'username', 'pass123', host=False, method='ssh')
print(b.get_sfs())
b.close()  # cleanup ( close session )
# del b  # cleanup ( close session )

# connect to 10x via REST
c = cnhelper.Dnfvi('172.17.143.26', 'username', 'pass123', method='REST')
print(c.get_sfs())
print(c.rest_apicall("GET", '/rest/vnf/file_mgmt/show/formatted'))  # custom REST call

# connect to cn_core_host regardless of system
d = cnhelper.Dnfvi('172.17.143.26', 'username', 'pass123', host=True)
print(d.host_cnfp_int_stat())
d.close()  # cleanup ( close session )
# del d  # cleanup ( close session )

e = cnhelper.Dnfvi('172.17.143.26', 'netconf-user', 'pass123', method='netconf')
print(e.get_sfs())
print(e._netconf_get('/nfvi/nfvi-state'))  # custom xpath get
e.close()  # cleanup ( close session )
# del e  # cleanup ( close session )

# connect to saos
f = cnhelper.Saos('172.17.143.27', 'username', 'pass123')
print(f.int_status())
print(f._send_cmd('flow mac show'))
f.close()  # cleanup ( close session )
# del f  # cleanup ( close session )

g = cnhelper.Saos('172.17.143.27', 'netconf-user', 'pass123', 'netconf')
print(g._netconf_get('//interfaces/interface'))  # custom xpath get
g.close()  # cleanup ( close session )
# del g  # cleanup ( close session )

