import json
import hashlib
import datetime
from enum import Enum
import math
import redis
import re
from zhconv import convert
from collections import defaultdict
import numpy as np


class IntEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.int32):
            return int(obj)
        else:
            return json.JSONEncoder.default(self, obj)


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


def get_redis():
    pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
    r = redis.Redis(connection_pool=pool)
    return r


def are_non_none_values_consecutive(my_list):
    for i in range(len(my_list)):
        if my_list[i] is None:
            return all(item is None for item in my_list[i:])
    return True


def unique_by_container_attr(elements, key=None):
    grouped = defaultdict(list)
    for element in elements:
        grouped[element[key]].append(element)
    group_count = {key: len(value) for key, value in grouped.items()}
    return group_count


def filter_party_name(name):
    name = str(name)
    tem_company_name = convert(name.split('@')[0].split(':')[-1], 'zh-cn')
    company_name_list = re.findall('[\u4e00-\u9fa5]+', tem_company_name, flags=0)
    company_name = ''.join(company_name_list)
    if company_name != '':
        return company_name.replace('通知人', '').split('公司')[0] + '公司'
    else:
        return 'TO ORDER'


def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        dict_data = json.loads(json_file.read())
    return dict_data


def save_json(dict_obj, file_path):
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(dict_obj, json_file, ensure_ascii=False)


def to_double(pile_str):
    if ~isinstance(pile_str, str):
        pile_str = str(pile_str)

    if len(pile_str) == 1:
        pile_str = f'''0{pile_str}'''

    return pile_str


def get_cache_key(req_dict):
    json_str = json.dumps(req_dict, separators=(',', ':'))
    hl = hashlib.md5()
    hl.update(json_str.encode(encoding='utf-8'))
    return hl.hexdigest()


def get_md5(str_to):
    hl = hashlib.md5()
    hl.update(str_to.encode(encoding='utf-8'))
    return hl.hexdigest()


def get_pile_split(pile_place):
    container_block = pile_place[0:2]
    container_bay = int(pile_place[2:4])
    container_row = int(pile_place[4:6])
    container_layer = None
    if len(pile_place) == 7:
        container_layer = int(pile_place[6:7])
    return container_bay, container_row, container_layer, container_block


def query_db(query, args=(), one=False):
    cur = database().cursor()
    cur.execute(query, args)
    r = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
    cur.connection.close()
    tem_result = (r[0] if r else None) if one else r
    return json.dumps(tem_result, cls=DateEncoder, ensure_ascii=False)


class Color(Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37


def print_color(text: str, fg: Color = Color.BLACK.value):
    # print(text)
    return


def count_dist_by_pile_place(start, end, op_type, options):
    start_bay, start_row, start_layer, _ = get_pile_split(start)
    end_bay, end_row, end_layer, _ = get_pile_split(end)
    mini_car_dist = 0
    huge_car_dist = 0
    final_pile = None
    if op_type == 'enter':
        if end_row < (options.yard_height / 2):
            mini_car_dist += (end_row - 1)
            final_pile = f'''{options.block}{to_double(end_bay)}{to_double(1)}'''
        else:
            mini_car_dist += (options.yard_height - end_row)
            final_pile = f'''{options.block}{to_double(end_bay)}{to_double(options.yard_height)}'''
        huge_car_dist = math.fabs((start_bay - end_bay) / 2)
        mini_car_dist += math.fabs(start_row - end_row)
    elif op_type == 'move':
        huge_car_dist = math.fabs((start_bay - end_bay) / 2)
        mini_car_dist = math.fabs(start_row - end_row)
        final_pile = end
    elif op_type == 'leave':
        huge_car_dist = math.fabs((start_bay - end_bay) / 2)
        mini_car_dist = math.fabs(start_row - end_row)
        if end_row < (options.yard_height / 2):
            mini_car_dist += (end_row - 1)
            final_pile = f'''{options.block}{to_double(end_bay)}{to_double(1)}'''
        else:
            mini_car_dist += (options.yard_height - end_row)
            final_pile = f'''{options.block}{to_double(end_bay)}{to_double(options.yard_height)}'''
    return final_pile, huge_car_dist, mini_car_dist


def get_forty_size_stack(pile_place):
    pile_bay, pile_row, pile_layer, pile_block = get_pile_split(pile_place)
    return f'{pile_block}{to_double(pile_bay - 1)}{to_double(pile_row)}'
