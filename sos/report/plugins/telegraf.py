# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Telegraf(Plugin, IndependentPlugin):

    short_desc = "Telegraf data collection agent"

    plugin_name = 'telegraf'
    profiles = ('monitoring', 'observability')
    packages = ('telegraf',)
    services = ('telegraf',)

    def setup(self):
        """ Telegraf, a server-based agent, collects and sends metrics and
            events from databases, systems, and IoT sensors.
        """

        self.add_copy_spec([
            '/etc/telegraf',
            '/etc/default/telegraf'
        ])

        config_file = '/etc/telegraf/telegraf.conf'

        telegraf_log_file = '/var/log/telegraf.log'

        try:
            with open(config_file, 'r', encoding='UTF-8') as cfile:
                for line in cfile.read().splitlines():
                    if not line:
                        continue
                    words = line.split('=')
                    if words[0].strip() == 'logfile':
                        telegraf_log_file = words[1].strip()
        except IOError as error:
            self._log_error(f'Could not open conf file {config_file}: {error}')

        if not self.get_option("all_logs"):
            self.add_copy_spec([
                telegraf_log_file,
            ])
        else:
            self.add_copy_spec([
                f"{telegraf_log_file}*",
            ])

# vim: set et ts=4 sw=4 :
