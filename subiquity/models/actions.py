# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import copy
import yaml


class NetAction():
    def __init__(self, **options):
        for k, v in options.items():
            setattr(self, k, v)
        self._action_keys = ['type', 'name', 'params', 'subnets']

    def get(self):
        action = {k: v for k, v in self.__dict__.items()
                  if k in self._action_keys}
        return action


class PhysicalAction(NetAction):
    def __init__(self, **options):
        if 'type' not in options or options['type'] != 'physical':
            raise Exception('Invalid type for {}'.format(
                self.__class__.__name__))
        if 'name' not in options or len(options['name']) == 0:
            raise Exception('Invalid name for {}'.format(
                self.__class__.__name__))
        if 'mac_address' not in options:
            raise Exception('{} requires a valid mac_address attr'.format(
                self.__class__.__name__))
        super().__init__(**options)
        self._action_keys.extend(['mac_address'])


class BridgeAction(NetAction):
    def __init__(self, **options):
        if 'type' not in options or options['type'] != 'bridge':
            raise Exception('Invalid type for {}'.format(
                self.__class__.__name__))
        if 'name' not in options or len(options['name']) == 0:
            raise Exception('Invalid name for {}'.format(
                self.__class__.__name__))
        if 'bridge_interfaces' not in options:
            raise Exception('{} requires bridge_interfaces attr'.format(
                self.__class__.__name__))
        super().__init__(**options)
        self._action_keys.extend(['bridge_interfaces'])


class VlanAction(NetAction):
    def __init__(self, **options):
        if 'type' not in options or options['type'] != 'vlan':
            raise Exception('Invalid type for {}'.format(
                self.__class__.__name__))
        if 'name' not in options or len(options['name']) == 0:
            raise Exception('Invalid name for {}'.format(
                self.__class__.__name__))
        if 'vlan_id' not in options or 'vlan_link' not in options:
            raise Exception('{} requires vlan_id and vlan_link attr'.format(
                self.__class__.__name__))
        super().__init__(**options)
        self._action_keys.extend(['vlan_id', 'vlan_link'])


class BondAction(NetAction):
    def __init__(self, **options):
        if 'type' not in options or options['type'] != 'bond':
            raise Exception('Invalid type for {}'.format(
                self.__class__.__name__))
        if 'name' not in options or len(options['name']) == 0:
            raise Exception('Invalid name for {}'.format(
                self.__class__.__name__))
        if 'bond_interfaces' not in options:
            raise Exception('{} requires bond_interfaces attr'.format(
                self.__class__.__name__))
        super().__init__(**options)
        self._action_keys.extend(['bond_interfaces'])


class DiskAction():
    def __init__(self, action_id, model, serial, ptable='gpt', wipe=None):
        self._action_id = action_id
        self.parent = None
        self._ptable = ptable
        self._model = model
        self._serial = serial
        self._wipe = wipe

    def get_parent(self):
        return self.parent

    @property
    def action_id(self):
        return str(self._action_id)

    def get(self):
        action = {
            'id': self.action_id,
            'model': self._model,
            'ptable': self._ptable,
            'serial': self._serial,
            'type': 'disk',
        }
        if self._wipe:
            action.update({'wipe': self._wipe})
        return action

    def dump(self):
        return yaml.dump(self.get(), default_flow_style=False)


class PartitionAction(DiskAction):
    def __init__(self, parent, partnum, offset, size, flags=None):
        self.parent = parent
        self.partnum = int(partnum)
        self._offset = int(offset)
        self._size = int(size)
        self.flags = flags
        self._action_id = "{}{}_part".format(self.parent.action_id,
                                             self.partnum)

        ''' rename action_id for readability '''
        if self.flags in ['bios_grub']:
            self._action_id = 'bios_boot_partition'

    @property
    def path(self):
        return "{}{}".format(self.parent.action_id, self.partnum)

    @property
    def size(self):
        return self._size

    @property
    def offset(self):
        return self._offset

    def get(self):
        return {
            'device': self.parent.action_id,
            'flag': self.flags,
            'id': self.action_id,
            'number': self.partnum,
            'size': '{}B'.format(self.size),
            'offset': '{}B'.format(self.offset),
            'type': 'partition',
        }


class BcacheAction(DiskAction):
    def __init__(self, backing_id, cache_id, bcache_num):
        self.parent = None
        self.bcachenum = int(bcache_num)
        self.backing_device = backing_id.parent.action_id
        self.cache_device = cache_id.parent.action_id
        self._action_id = "bcache" + str(bcache_num)

    def get(self):
        return {
            'backing_device': self.backing_device,
            'cache_device': self.cache_device,
            'id': self.action_id,
            'type': 'bcache',
        }


class FormatAction(DiskAction):
    def __init__(self, parent, fstype):
        self.parent = parent
        self._fstype = fstype
        self._action_id = "{}_fmt".format(self.parent.action_id)
        # fat filesystem require an id of <= 11 chars
        if fstype.startswith('fat'):
            self._action_id = self._action_id[:11]
        # curtin detects fstype as 'swap'
        elif fstype.startswith('linux-swap'):
            self._fstype = 'swap'

    @property
    def fstype(self):
        return self._fstype

    def get(self):
        return {
            'volume': self.parent.action_id,
            'id': self.action_id,
            'fstype': self.fstype,
            'type': 'format',
        }


class MountAction(DiskAction):
    def __init__(self, parent, path):
        self.parent = parent
        self._path = path
        self._action_id = "{}_mnt".format(self.parent.action_id)

    @property
    def path(self):
        return self._path

    def get(self):
        return {
            'device': self.parent.action_id,
            'id': self.action_id,
            'path': self.path,
            'type': 'mount',
        }


def preserve_action(action):
    a = copy.deepcopy(action)
    a.update({'preserve': True})
    return a


def release_action(action):
    a = copy.deepcopy(action)
    if 'preserve' in action:
        del a['preserve']
    return a
