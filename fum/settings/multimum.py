from base import *
from prod import *

LDAP_CONNECTION = {
    'uri': "ldap://ldapng-qa2.futurice.com",
    'bind_dn': "uid=fum3adm,ou=Administrators,ou=TopologyManagement,o=Netscaperoot",
    'bind_pwd': "njJc4RUWJVre",
    'base_dn': COMPANY_DN,
}
