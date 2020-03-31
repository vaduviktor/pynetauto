import cnhelper

# connect to ui ( 18x system )
a = cnhelper.Dnfvi('172.17.143.18', 'username', '1234', host=False)
print(a.get_nfvi())

# connect to 10x cli
b = cnhelper.Dnfvi('172.17.143.26', 'username', '1234', host=False, method='ssh')
print(b.get_sffs())

# connect to 10x via REST
c = cnhelper.Dnfvi('172.17.143.26', 'username', '1234', method='REST')
print(c.get_sfs())

# connect to cn_core_host regardless of system
d = cnhelper.Dnfvi('172.17.143.26', 'username', '1234', host=True)
print(d.host_cnfp_int_stat())

# connect to saos
e = cnhelper.Saos('172.17.143.27', 'username', '1234')
print(e.int_status())
print(e._send_cmd('flow mac show'))


