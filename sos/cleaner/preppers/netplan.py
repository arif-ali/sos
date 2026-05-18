# Copyright 2026 Canonical Ltd. Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

import yaml

from sos.cleaner.preppers import SoSPrepper


class NetplanPrepper(SoSPrepper):
    """
    Prepper that seeds the hostname/domain mapping with values discovered
    in netplan YAML configurations, so that `sos clean` (and `sos report
    --clean`) obfuscates DNS search domains and DHCP hostname overrides
    that would otherwise not match the system's own FQDN.

    Netplan configs may live under /etc/netplan, /lib/netplan, or
    /run/netplan. Only the following keys are extracted here:

      - network.*.<iface>.nameservers.search   (list of domains)
      - network.*.<iface>.dhcp4-overrides.hostname
      - network.*.<iface>.dhcp6-overrides.hostname
    """

    name = 'netplan'
    # Run after the HostnamePrepper (priority 100) so that the host's own
    # FQDN is registered first; this keeps obfuscation counter assignment
    # deterministic across runs.
    priority = 110

    _netplan_dirs = ('etc/netplan', 'lib/netplan', 'run/netplan')
    _yaml_exts = ('.yaml', '.yml')

    def _iter_netplan_files(self, archive):
        """Yield archive-relative paths to netplan YAML files. Works both
        before extraction (tarball: enumerate tarobj members) and after
        (directory archive: walk the on-disk tree).
        """
        seen = set()

        tarobj = getattr(archive, 'tarobj', None)
        if tarobj is not None:
            try:
                root = archive.get_archive_root().rstrip('/')
                for name in tarobj.getnames():
                    rel = name
                    if root and rel.startswith(root + '/'):
                        rel = rel[len(root) + 1:]
                    if not rel.endswith(self._yaml_exts):
                        continue
                    if not any(rel.startswith(d + '/')
                               for d in self._netplan_dirs):
                        continue
                    if rel not in seen:
                        seen.add(rel)
                        yield rel
            except Exception as err:
                self.log_debug(f"failed to enumerate netplan files from "
                               f"tarball: {err}")
            return

        base = getattr(archive, 'extracted_path', None) or \
            getattr(archive, 'archive_path', None)
        if not base or not os.path.isdir(base):
            return
        for d in self._netplan_dirs:
            ndir = os.path.join(base, d)
            if not os.path.isdir(ndir):
                continue
            try:
                entries = os.listdir(ndir)
            except OSError as err:
                self.log_debug(f"failed to list {ndir}: {err}")
                continue
            for entry in entries:
                if entry.endswith(self._yaml_exts):
                    rel = os.path.join(d, entry)
                    if rel not in seen:
                        seen.add(rel)
                        yield rel

    def _walk_ifaces(self, doc):
        """Yield each per-interface mapping found under a netplan document.

        Netplan groups interfaces under top-level type keys (ethernets,
        wifis, bridges, bonds, vlans, vrfs, tunnels, dummy-devices, ...).
        We don't enumerate the type set explicitly: any mapping under
        `network` whose value is itself a mapping of named interfaces is
        treated the same way.
        """
        if not isinstance(doc, dict):
            return
        network = doc.get('network')
        if not isinstance(network, dict):
            return
        for type_key, type_val in network.items():
            if type_key in ('version', 'renderer'):
                continue
            if not isinstance(type_val, dict):
                continue
            for iface_cfg in type_val.values():
                if isinstance(iface_cfg, dict):
                    yield iface_cfg

    def _collect_from_iface(self, iface, items, hostnames):
        nameservers = iface.get('nameservers')
        if isinstance(nameservers, dict):
            search = nameservers.get('search')
            if isinstance(search, list):
                for entry in search:
                    if isinstance(entry, str) and '.' in entry:
                        items.append(entry.strip().lower())

        for key in ('dhcp4-overrides', 'dhcp6-overrides'):
            override = iface.get(key)
            if isinstance(override, dict):
                host = override.get('hostname')
                if isinstance(host, str) and host.strip():
                    host = host.strip()
                    if '.' in host:
                        items.append(host.lower())
                    else:
                        hostnames.add(host)

    def _get_items_for_hostname(self, archive):
        items = []
        hostnames = set()

        for rel in self._iter_netplan_files(archive):
            content = archive.get_file_content(rel)
            if not content:
                continue
            try:
                doc = yaml.safe_load(content)
            except yaml.YAMLError as err:
                self.log_debug(f"skipping malformed netplan file {rel}: {err}")
                continue
            for iface in self._walk_ifaces(doc):
                self._collect_from_iface(iface, items, hostnames)

        for host in hostnames:
            self.regex_items['hostname'].add(host)

        return items

# vim: set et ts=4 sw=4 :
