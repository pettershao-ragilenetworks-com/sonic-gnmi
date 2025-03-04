
import os
import json
import time
from utils import gnmi_set, gnmi_get, gnmi_dump

import pytest


test_data_update_normal = [
    [
        {
            'path': '/sonic-db:CONFIG_DB/PORT',
            'value': {
                'Ethernet4': {'admin_status': 'down'},
                'Ethernet8': {'admin_status': 'down'}
            }
        }
    ],
    [
        {
            'path': '/sonic-db:CONFIG_DB/PORT/Ethernet4/admin_status',
            'value': 'up'
        },
        {
            'path': '/sonic-db:CONFIG_DB/PORT/Ethernet8/admin_status',
            'value': 'up'
        }
    ],
    [
        {
            'path': '/sonic-db:CONFIG_DB/PORT/Ethernet4',
            'value': {'admin_status': 'down'}
        },
        {
            'path': '/sonic-db:CONFIG_DB/PORT/Ethernet8',
            'value': {'admin_status': 'down'}
        }
    ]
]

test_json_checkpoint = {
    "DASH_QOS": {
        'qos_01': {'bw': '54321', 'cps': '1000', 'flows': '300'},
        'qos_02': {'bw': '6000', 'cps': '200', 'flows': '101'}
    },
    "DASH_VNET": {
        'vnet_3721': {
            'address_spaces': ["10.250.0.0", "192.168.3.0", "139.66.72.9"]
        }
    }
}

test_data_checkpoint = [
    [
        {
            'path': '/sonic-db:CONFIG_DB/DASH_QOS',
            'value': {
                'qos_01': {'bw': '54321', 'cps': '1000', 'flows': '300'},
                'qos_02': {'bw': '6000', 'cps': '200', 'flows': '101'}
            }
        },
        {
            'path': '/sonic-db:CONFIG_DB/DASH_VNET',
            'value': {
                'vnet_3721': {
                    'address_spaces': ["10.250.0.0", "192.168.3.0", "139.66.72.9"]
                }
            }
        }
    ],
    [
        {
            'path': '/sonic-db:CONFIG_DB/DASH_QOS/qos_01',
            'value': {'bw': '54321', 'cps': '1000', 'flows': '300'},
        },
        {
            'path': '/sonic-db:CONFIG_DB/DASH_QOS/qos_02',
            'value': {'bw': '6000', 'cps': '200', 'flows': '101'}
        },
        {
            'path': '/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721',
            'value': {
                'address_spaces': ["10.250.0.0", "192.168.3.0", "139.66.72.9"]
            }
        }
    ],
    [
        {
            'path': '/sonic-db:CONFIG_DB/DASH_QOS/qos_01/flows',
            'value': '300'
        },
        {
            'path': '/sonic-db:CONFIG_DB/DASH_QOS/qos_02/bw',
            'value': '6000'
        },
        {
            'path': '/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721/address_spaces',
            'value': ["10.250.0.0", "192.168.3.0", "139.66.72.9"]
        }
    ],
    [
        {
            'path': '/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721/address_spaces/0',
            'value': "10.250.0.0"
        },
        {
            'path': '/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721/address_spaces/1',
            'value': "192.168.3.0"
        }
    ]
]

patch_file = '/tmp/gcu.patch'
config_file = '/tmp/config_db.json.tmp'
checkpoint_file = '/etc/sonic/config.cp.json'

def create_dir(path):
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)

def create_checkpoint(file_name, text):
    create_dir(os.path.dirname(file_name))
    file_object = open(file_name, 'w')
    file_object.write(text)
    file_object.close()
    return

class TestGNMIConfigDb:

    @pytest.mark.parametrize("test_data", test_data_update_normal)
    def test_gnmi_incremental_update(self, test_data):
        create_checkpoint(checkpoint_file, '{}')

        update_list = []
        for i, data in enumerate(test_data):
            path = data['path']
            value = json.dumps(data['value'])
            file_name = 'update' + str(i)
            file_object = open(file_name, 'w')
            file_object.write(value)
            file_object.close()
            update_list.append(path + ':@./' + file_name)

        ret, old_apply_patch_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        ret, old_create_checkpoint_cnt = gnmi_dump("DBUS create checkpoint")
        assert ret == 0, 'Fail to read counter'
        ret, old_delete_checkpoint_cnt = gnmi_dump("DBUS delete checkpoint")
        assert ret == 0, 'Fail to read counter'
        ret, old_config_save_cnt = gnmi_dump("DBUS config save")
        assert ret == 0, 'Fail to read counter'
        ret, msg = gnmi_set([], update_list, [])
        assert ret == 0, msg
        assert os.path.exists(patch_file), "No patch file"
        with open(patch_file,'r') as pf:
            patch_json = json.load(pf)
        for item in test_data:
            test_path = item['path']
            test_value = item['value']
            for patch_data in patch_json:
                assert patch_data['op'] == 'add', "Invalid operation"
                if test_path == '/sonic-db:CONFIG_DB' + patch_data['path'] and test_value == patch_data['value']:
                    break
            else:
                pytest.fail('No item in patch: %s'%str(item))
        ret, new_apply_patch_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        assert new_apply_patch_cnt == old_apply_patch_cnt + 1, 'DBUS API is not invoked'
        ret, new_create_checkpoint_cnt = gnmi_dump("DBUS create checkpoint")
        assert ret == 0, 'Fail to read counter'
        assert new_create_checkpoint_cnt == old_create_checkpoint_cnt + 1, 'DBUS API is not invoked'
        ret, new_delete_checkpoint_cnt = gnmi_dump("DBUS delete checkpoint")
        assert ret == 0, 'Fail to read counter'
        assert new_delete_checkpoint_cnt == old_delete_checkpoint_cnt + 1, 'DBUS API is not invoked'
        ret, new_config_save_cnt = gnmi_dump("DBUS config save")
        assert ret == 0, 'Fail to read counter'
        assert new_config_save_cnt == old_config_save_cnt + 1, 'DBUS API is not invoked'

    @pytest.mark.parametrize("test_data", test_data_checkpoint)
    def test_gnmi_incremental_delete(self, test_data):
        create_checkpoint(checkpoint_file, json.dumps(test_json_checkpoint))

        if os.path.exists(patch_file):
            os.remove(patch_file)
        delete_list = []
        for i, data in enumerate(test_data):
            path = data['path']
            delete_list.append(path)
        ret, old_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        ret, msg = gnmi_set(delete_list, [], [])
        assert ret == 0, msg
        assert os.path.exists(patch_file), "No patch file"
        with open(patch_file,'r') as pf:
            patch_json = json.load(pf)
        for item in test_data:
            test_path = item['path']
            for patch_data in patch_json:
                assert patch_data['op'] == 'remove', "Invalid operation"
                if test_path == '/sonic-db:CONFIG_DB' + patch_data['path']:
                    break
            else:
                pytest.fail('No item in patch: %s'%str(item))
        ret, new_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        assert new_cnt == old_cnt+1, 'DBUS API should not be invoked'

    @pytest.mark.parametrize("test_data", test_data_update_normal)
    def test_gnmi_incremental_delete_negative(self, test_data):
        create_checkpoint(checkpoint_file, '{}')
        if os.path.exists(patch_file):
            os.remove(patch_file)

        delete_list = []
        for i, data in enumerate(test_data):
            path = data['path']
            delete_list.append(path)

        ret, old_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        ret, msg = gnmi_set(delete_list, [], [])
        assert ret == 0, msg
        assert not os.path.exists(patch_file), "Should not generate patch file"
        ret, new_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        assert new_cnt == old_cnt, 'DBUS API should not be invoked'

    @pytest.mark.parametrize("test_data", test_data_update_normal)
    def test_gnmi_incremental_replace(self, test_data):
        create_checkpoint(checkpoint_file, '{}')

        replace_list = []
        for i, data in enumerate(test_data):
            path = data['path']
            value = json.dumps(data['value'])
            file_name = 'update' + str(i)
            file_object = open(file_name, 'w')
            file_object.write(value)
            file_object.close()
            replace_list.append(path + ':@./' + file_name)

        ret, old_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        ret, msg = gnmi_set([], [], replace_list)
        assert ret == 0, msg
        assert os.path.exists(patch_file), "No patch file"
        with open(patch_file,'r') as pf:
            patch_json = json.load(pf)
        for item in test_data:
            test_path = item['path']
            test_value = item['value']
            for patch_data in patch_json:
                assert patch_data['op'] == 'add', "Invalid operation"
                if test_path == '/sonic-db:CONFIG_DB' + patch_data['path'] and test_value == patch_data['value']:
                    break
            else:
                pytest.fail('No item in patch: %s'%str(item))
        ret, new_cnt = gnmi_dump("DBUS apply patch db")
        assert ret == 0, 'Fail to read counter'
        assert new_cnt == old_cnt+1, 'DBUS API is not invoked'

    def test_gnmi_full(self):
        test_data = {
            'field_01': '20001',
            'field_02': '20002',
            'field_03': '20003',
            'field_04': {'item_01': 'aaaa', 'item_02': 'xxxxx'}
        }
        file_name = 'config_db.test'
        file_object = open(file_name, 'w')
        value = json.dumps(test_data)
        file_object.write(value)
        file_object.close()
        delete_list = ['/sonic-db:CONFIG_DB/']
        update_list = ['/sonic-db:CONFIG_DB/' + ':@./' + file_name]

        ret, msg = gnmi_set(delete_list, update_list, [])
        assert ret == 0, msg
        assert os.path.exists(config_file), "No config file"
        with open(config_file,'r') as cf:
            config_json = json.load(cf)
        assert test_data == config_json, "Wrong config file"

    def test_gnmi_full_negative(self):
        delete_list = ['/sonic-db:CONFIG_DB/']
        update_list = ['/sonic-db:CONFIG_DB/' + ':abc']

        ret, msg = gnmi_set(delete_list, update_list, [])
        assert ret != 0, 'Invalid ietf_json_val'
        assert 'IETF JSON' in msg

    @pytest.mark.parametrize("test_data", test_data_checkpoint)
    def test_gnmi_get_checkpoint(self, test_data):
        if os.path.isfile(checkpoint_file):
            os.remove(checkpoint_file)

        get_list = []
        for data in test_data:
            path = data['path']
            get_list.append(path)

        ret, msg_list = gnmi_get(get_list)
        if ret == 0:
            for msg in msg_list:
                assert msg == '{}', 'Invalid result'

        text = json.dumps(test_json_checkpoint)
        create_checkpoint(checkpoint_file, text)

        get_list = []
        for data in test_data:
            path = data['path']
            value = json.dumps(data['value'])
            get_list.append(path)

        ret, msg_list = gnmi_get(get_list)
        assert ret == 0, 'Invalid return code'
        assert len(msg_list), 'Invalid msg: ' + str(msg_list)
        for data in test_data:
            hit = False
            for msg in msg_list:
                rx_data = json.loads(msg)
                if data['value'] == rx_data:
                    hit = True
                    break
            assert hit == True, 'No match for %s'%str(data['value'])

    def test_gnmi_get_checkpoint_negative_01(self):
        text = json.dumps(test_json_checkpoint)
        create_checkpoint(checkpoint_file, text)

        get_list = ['/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721/address_spaces/0/abc']
 
        ret, _ = gnmi_get(get_list)
        assert ret != 0, 'Invalid path'

    def test_gnmi_get_checkpoint_negative_02(self):
        text = json.dumps(test_json_checkpoint)
        create_checkpoint(checkpoint_file, text)

        get_list = ['/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721/address_spaces/abc']
 
        ret, _ = gnmi_get(get_list)
        assert ret != 0, 'Invalid path'

    def test_gnmi_get_checkpoint_negative_03(self):
        text = json.dumps(test_json_checkpoint)
        create_checkpoint(checkpoint_file, text)

        get_list = ['/sonic-db:CONFIG_DB/DASH_VNET/vnet_3721/address_spaces/1000']
 
        ret, _ = gnmi_get(get_list)
        assert ret != 0, 'Invalid path'

