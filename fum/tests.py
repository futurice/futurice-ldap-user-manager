import sshpubkeys
import unittest


class UtilTestCase(unittest.TestCase):

    def test_ssh_key_bits_and_fingerprint(self):
        with self.assertRaises(sshpubkeys.InvalidKeyException):
            sshpubkeys.SSHKey('an invalid key string')

        valid_ssh_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC3uta/x/kAwbs2G7AOUQtRG7l1hjEws4mrvnTZmwICoGNi+TUwxerZgMbBBID7Kpza/ZSUqXpKX5gppRW9zECBsbJ+2D0ch/oVSZ408aUE6ePNzJilLA/2wtRct/bkHDZOVI+iwEEr1IunjceF+ZQxnylUv44C6SgZvrDj+38hz8z1Vf4BtW5jGOhHkddTadU7Nn4jQR3aFXMoheuu/vHYD2OyDJj/r6vh9x5ey8zFmwsGDtFCCzzLgcfPYfOdDxFIWhsopebnH3QHVcs/E0KqhocsEdFDRvcFgsDCKwmtHyZVAOKym2Pz9TfnEdGeb+eKrleZVsApFrGtSIfcf4pH user@host'
        ssh_key = sshpubkeys.SSHKey(valid_ssh_key)
        self.assertEqual(ssh_key.bits, 2048)
        self.assertEqual(ssh_key.hash(),
                '73:e7:0c:60:7b:d2:7b:df:81:2e:c2:57:54:53:81:91')
