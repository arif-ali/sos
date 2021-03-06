# Copyright (C) 2007 Ranjith Rajaram <rrajaram@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Quagga(Plugin, RedHatPlugin):
    """Quagga routing service
    """

    plugin_name = 'quagga'
    profiles = ('network',)

    files = ('/etc/quagga/zebra.conf',)
    packages = ('quagga',)

    def setup(self):
        self.add_copy_spec("/etc/quagga/")

# vim: set et ts=4 sw=4 :
