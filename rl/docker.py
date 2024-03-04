import utils
import json
import datetime
import joblib
import pandas as pd
import numpy as np
from random import choice
from tqdm import tqdm


# 初始化配置
class DockerGameOptions:
    def __init__(
            self,
            block,
            yard_width,
            yard_height,
            yard_depth,
            init_time='2021-08-21 20:46:56',
            target_time='2021-08-27 23:59:58',
            with_predict=True,
            train_type=4
    ):
        """
            container position code like '0102104'
            01: block
            02: bay (40ft container is double bay, 20ft container is single bay)
            10: row
            4: tier
        """
        self.block = block
        self.yard_width = yard_width
        self.yard_height = yard_height
        self.yard_depth = yard_depth
        self.init_time = init_time
        self.target_time = target_time
        self.train_type = train_type
        self.with_predict = with_predict


# 码头翻箱游戏
class DockerGame:
    def __init__(self, options):
        self.options = options

        # progress bar
        self.is_progress = True
        self.progress_bar = None
        if self.is_progress:
            self.progress_bar = None
            self.progress_bar_total = 0
            self.progress_bar_current = 0
            self.progress_bar_description = ''
        # game config
        # is game over
        self.game_over = False
        # bay map
        self.block_bay_info_map = None
        # stack map
        self.yard_stack_map = {}
        # container info map
        self.current_container_map = {}
        # container bill lading map
        self.container_bill_map = {}
        # current time
        self.current_time = None
        # operation waiting list
        self.operation_list = []
        # machine position after last operation
        self.mc_last_position = None
        # disable stack
        self.disable_stack = None
        # svr predict map
        self.pred_map = {}
        # bill lading info map
        self.cache_bill_map = {}
        # consignor info map
        self.cache_consignor_map = {}

        # game status
        # reload count
        self.reload_count = 0
        # twice reload count
        self.reload_twice_count = 0
        # leave count
        self.leave_count = 0
        # enter count
        self.enter_count = 0
        # huge car distance
        self.huge_car_dist = 0
        # mini car distance
        self.mini_car_dist = 0
        # used rate
        self.used_rate = 0
        # reward list
        self.reward_list = []
        # action history
        self.action_list = []
        # total reward (equals sum of reward list)
        self.total_reward = 0
        # reward type
        # 1: only consider reload times and twice reload times
        # 2: only consider huge car distance and mini car distance
        # 3: only rule
        # 4: all

        # reward map
        self.reward_map = {
            'finish': 99999,
            'zero_cover_num': 2,
            'replace_times_num': 2,
            'huge_car': 17.6,
            'min_car': 2.4,
            'cover_predict': 1,
            'cover_expire': 2,
            'long_day': 6,
            'mix_score': 6,
            'same_bill_lading': 4,
            'same_party': 4,
            'bind_container': 3,
            'book_container': 3,
            'used_container': 3,
            'check_container': 3,
            'block_container': 3,
            'relocation_times': 40,
            'twice_relocation_times': 5,
            'assign_container': 1,
            'leave_success': 600,
            'enter_success': 600
        }

        # redis for cache
        self.redis = None

    # update current time after each operation
    def update_current_time(self, ct):
        self.current_time = ct

    # init bill lading map and consignor map
    def init_map(self):
        self.cache_bill_map = utils.read_json('../datasets/json/cache_bill_map.json')
        self.cache_consignor_map = utils.read_json('../datasets/json/cache_consignor_map.json')

    # game start
    def create_game(self):
        self.reset()
        self.init_map()
        self.init_yard_container()
        self.get_operation_list()
        self.get_bill_map_status()
        self.predict_container()
        self.create_yard()
        self.update_container_status()
        if self.is_progress:
            self.progress_bar = tqdm()
            print(
                f'Create game success, current time: {self.current_time}, operation length: {len(self.operation_list)}')
            self.progress_bar.total = len(self.operation_list)

    def add_process_total(self, total):
        self.progress_bar.total += total

    def update_process(self):
        self.progress_bar.update(1)
        self.progress_bar_description = f'Current time: {self.current_time}, operation length: {len(self.operation_list)}, reward: {sum(self.reward_list)}, reload count: {self.reload_count}, reload twice count: {self.reload_twice_count}, huge_car_dist: {self.huge_car_dist}, mini_car_dist: {self.mini_car_dist}'
        self.progress_bar_total = self.progress_bar.total
        self.progress_bar_current = self.progress_bar.n
        self.progress_bar.set_description(self.progress_bar_description)

    # get container bill info
    def get_bill_map_status(self):
        bill_lading_list = json.loads(self.get_yard_container_bill_lading())
        self.container_bill_map = {}
        for bill_lading in bill_lading_list:
            if bill_lading['CONTAINER_REF_ID'] not in self.container_bill_map:
                self.container_bill_map[bill_lading['CONTAINER_REF_ID']] = [bill_lading]
            else:
                self.container_bill_map[bill_lading['CONTAINER_REF_ID']].append(bill_lading)
            if 'BILL_LADING_REF_ID' in bill_lading and bill_lading['BILL_LADING_REF_ID'] not in self.cache_bill_map:
                self.cache_bill_map[bill_lading['BILL_LADING_REF_ID']] = len(self.cache_bill_map.keys()) + 1
            if 'CONSIGNOR_NAME' in bill_lading and bill_lading['CONSIGNOR_NAME'] not in self.cache_consignor_map:
                self.cache_consignor_map[bill_lading['CONSIGNOR_NAME']] = len(self.cache_consignor_map.keys()) + 1
        # utils.save_json(self.cache_bill_map, '../datasets/json/cache_bill_map.json')
        # utils.save_json(self.cache_consignor_map, '../datasets/json/cache_consignor_map.json')

    def get_used_rate(self):
        count = 0
        for ref_id in self.current_container_map:
            current_container = self.current_container_map[ref_id]
            container_size = int(current_container['CONTAINER_TYPE'][0:2])
            if container_size == 20:
                count += 1
            elif container_size == 40:
                count += 2
        self.used_rate = (count * 100 / (self.options.yard_width * self.options.yard_height * self.options.yard_depth))

    # get predict data by using svr model
    def predict_container(self):
        ref_id_list = list(self.current_container_map.keys())
        future_ref_id_list = [operation['CONTAINER_REF_ID'] for operation in self.operation_list]
        ref_id_list.extend(future_ref_id_list)
        ref_id_list.sort()
        cache_key = utils.get_cache_key({
            'containerRefIds': ref_id_list
        })
        cache_key = f'''pc_{cache_key}'''
        result = self.redis.get(cache_key)
        final_result = json.loads(result)

        current_pd = pd.DataFrame(final_result)
        current_pd['UNLOAD_SORT'] = list(range(0, len(final_result)))
        p_data_x, predict_columns, source_data = self.predict_data(current_pd)
        clf = joblib.load('../predict/model/svm/svr_model.pkl')
        self.pred_map = {}
        pred_delay_list = clf.predict(p_data_x)
        pred_delay_list = json.loads(pd.DataFrame({
            'CONTAINER_REF_ID': source_data['CONTAINER_REF_ID'],
            'PRE_DIFF': pred_delay_list
        }).to_json(orient='records'))
        for pred_item in pred_delay_list:
            self.pred_map[pred_item['CONTAINER_REF_ID']] = pred_item['PRE_DIFF']
        for operation in self.operation_list:
            if operation['CONTAINER_REF_ID'] in self.pred_map:
                operation['PRE_DIFF'] = self.pred_map[operation['CONTAINER_REF_ID']]
                if operation['ACTION'] == 'enter':
                    operation['REL_DIFF'] = 0
                else:
                    operation['REL_DIFF'] = (datetime.datetime.strptime(self.current_time,
                                                                        '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                        operation['IN_DATE'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60 / 60 / 24
                operation['PRE_DATE'] = (datetime.datetime.strptime(operation['IN_DATE'],
                                                                    '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                    days=operation['PRE_DIFF'])).strftime('%Y-%m-%d %H:%M:%S')
        return result

    # update predict data when current time change
    def update_yard_container_predict(self):
        for ref_id in self.current_container_map:
            current_container = self.current_container_map[ref_id]
            if ref_id in self.pred_map:
                current_container['PRE_DATE'] = (datetime.datetime.strptime(current_container['IN_DATE'],
                                                                            '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                    days=self.pred_map[ref_id])).strftime('%Y-%m-%d %H:%M:%S')
                current_container['REAL_DIFF'] = (datetime.datetime.strptime(
                    self.current_time, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                    current_container['IN_DATE'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60 / 60 / 24
                current_container['REMAIN_DIFF'] = (datetime.datetime.strptime(
                    current_container['PRE_DATE'], '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                    self.current_time, '%Y-%m-%d %H:%M:%S')).total_seconds() / 60 / 60 / 24
            else:
                current_container['REAL_DIFF'] = (datetime.datetime.strptime(
                    self.current_time, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                    current_container['IN_DATE'], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60 / 60 / 24

    # update container status after each operation
    def update_container_status(self):
        if len(self.operation_list) > 0:
            self.current_time = self.operation_list[0]['OP_TIME']
            self.get_yard_container_status()
            self.update_yard_container_predict()
            self.get_used_rate()

    # take an action
    def take_action(self, input_pile=None):
        if len(self.operation_list) > 0:
            success, action_type, score, pile_place, able_pile_place, block_container_id = self.action_step(input_pile)
            detail, enter_able_pile = self.next_container()
            if score is None:
                score = 0
            return success, action_type, score, pile_place, able_pile_place, block_container_id, detail, enter_able_pile
        else:
            score = self.count_reward('finish')
            self.close()
            self.update_process()
            return False, None, score, None, None, None, None, None

    def get_cur_info(self):
        """
        [
            use rate,
            reload count,
            twice reload count,
            leave count,
            reload rate,
            enter count,
            huge car distance,
            mini car distance,
            action list
        ]
        """
        return [
            self.used_rate,
            self.reload_count,
            self.reload_twice_count,
            self.leave_count,
            0 if self.leave_count == 0 else self.reload_count * 100 / self.leave_count,
            self.enter_count,
            self.huge_car_dist,
            self.mini_car_dist,
            self.action_list
        ]

    # get action space
    def get_action_space(self):
        stack_map = {}
        for i in range(1, self.options.yard_width * 2, 1):
            if i % 2 == 0:
                continue
            for j in range(1, self.options.yard_height + 1):
                # 1 for enter
                stack_map[len(stack_map.keys())] = [i, j, 1]
                # 3 for reload/move
                stack_map[len(stack_map.keys())] = [i, j, 3]
        stack_map[len(stack_map.keys())] = [0, 0, 2]
        return stack_map

    def get_observation_space(self):
        #  generate observation space
        stack_map = {}
        for i in range(1, self.options.yard_width * 2, 1):
            for j in range(1, self.options.yard_height + 1):
                for k in range(1, self.options.yard_depth + 1):
                    stack_code = f'''{self.options.block}{utils.to_double(i)}{utils.to_double(j)}{k}'''
                    if self.options.with_predict:
                        stack_map[stack_code] = [i, j, k] + [-1] * 19
                    else:
                        stack_map[stack_code] = [i, j, k] + [-1] * 17
        observation_space = []
        for ref_id in self.current_container_map:
            container = self.current_container_map[ref_id]
            if container['PILE_PLACE'] in stack_map:
                container_bay, container_row, container_tier, _ = utils.get_pile_split(container['PILE_PLACE'])
                attr_item = self.get_rl_status_by_container(container)
            stack_map[container['PILE_PLACE']] = [container_bay, container_row, container_tier] + attr_item + [0, 0]
        for key in stack_map:
            observation_space.append(stack_map[key])
        if len(self.operation_list) == 0:
            if self.options.with_predict:
                current_operation = [-1] * 22
            else:
                current_operation = [-1] * 20
            observation_space.append(current_operation)
        else:
            current_operation = self.operation_list[0]
            current_attr_item = self.get_rl_status_by_container(current_operation)
            if current_operation['ACTION'] == 'enter':
                observation_space.append([0, 0, 0] + current_attr_item + [1, 0])
            elif current_operation['ACTION'] == 'leave':
                container_bay, container_row, container_tier, _ = utils.get_pile_split(
                    self.current_container_map[current_operation['CONTAINER_REF_ID']]['PILE_PLACE'])
                observation_space.append([container_bay, container_row, container_tier] + current_attr_item + [2, 0])
            elif current_operation['ACTION'] == 'move':
                container_bay, container_row, container_tier, _ = utils.get_pile_split(
                    self.current_container_map[current_operation['CONTAINER_REF_ID']]['PILE_PLACE'])
                observation_space.append([container_bay, container_row, container_tier] + current_attr_item + [3, 0])
        return observation_space

    # get observation status
    def get_rl_status_by_container(self, container):
        child_item = []
        if container['IF_USED'] == 'Y':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['IF_CHECK'] == 'Y':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['IF_BLOCK'] == 'Y':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['IF_ASSIGN'] == 'Y':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['IF_BIND'] == 'Y':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['IF_BOOK'] == 'Y':
            child_item.append(1)
        else:
            child_item.append(0)
        if 'REAL_DIFF' in container:
            child_item.append(container['REAL_DIFF'])
        else:
            child_item.append(-1)

        if self.options.with_predict:
            if 'REMAIN_DIFF' in container:
                child_item.append(container['REMAIN_DIFF'])
            else:
                child_item.append(-1)
            if 'PRE_DIFF' in container:
                child_item.append(container['PRE_DIFF'])
            else:
                child_item.append(-1)
        if 'BILL_LADING_REF_ID' in container and container['BILL_LADING_REF_ID'] is not None:
            bill_ref_id_list = container['BILL_LADING_REF_ID'].split(',')
            if bill_ref_id_list[0] in self.cache_bill_map:
                child_item.append(self.cache_bill_map[bill_ref_id_list[0]])
            else:
                child_item.append(-1)
        else:
            child_item.append(-1)
        if container['CONTAINER_REF_ID'] in self.container_bill_map:
            consignor_name = self.container_bill_map[container['CONTAINER_REF_ID']][0]['CONSIGNOR_NAME']
            if consignor_name in self.cache_consignor_map:
                child_item.append(self.cache_consignor_map[consignor_name])
            else:
                child_item.append(-1)
        else:
            child_item.append(-1)
        container_size = int(container['CONTAINER_TYPE'][0:2])
        child_item.append(container_size)
        if container['INSIDE_OR_OUTSIDE'] == '外':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['IMPORT_OR_EXPORT'] == '进':
            child_item.append(1)
        else:
            child_item.append(0)
        if container['CONTAINER_STATE'] == '重':
            child_item.append(1)
        else:
            child_item.append(0)
        child_item.append(1)
        if 'REPLACE_TIMES' in container:
            child_item.append(container['REPLACE_TIMES'])
        else:
            child_item.append(0)
        return child_item

    # achieve next operation
    def next_container(self):
        self.operation_list = self.operation_list[1:len(self.operation_list)]
        if len(self.operation_list) > 0:
            self.update_container_status()
            self.create_yard()
            able_pile_list = self.get_able_pile_list()
            return [
                self.used_rate,
                self.reload_count,
                self.reload_twice_count,
                self.leave_count,
                0 if self.leave_count == 0 else self.reload_count * 100 / self.leave_count,
                self.enter_count,
                self.huge_car_dist,
                self.mini_car_dist
            ], able_pile_list
        else:
            return [
                self.used_rate,
                self.reload_count,
                self.reload_twice_count,
                self.leave_count,
                0 if self.leave_count == 0 else self.reload_count * 100 / self.leave_count,
                self.enter_count,
                self.huge_car_dist,
                self.mini_car_dist
            ], None

    # get able enter pile place
    def get_able_pile_list(self):
        able_pile_place = []
        for stack_code in self.yard_stack_map:
            current_stack = self.yard_stack_map[stack_code]
            stack_bay, stack_row, _, _ = utils.get_pile_split(stack_code)
            able_pile = self.get_able_enter(self.disable_stack, current_stack)
            if able_pile is not None and able_pile not in able_pile_place:
                able_pile_place.append(able_pile)
        return able_pile_place

    # get able enter pile place
    def get_able_enter(self, disable_stack, current_stack):
        current_container = self.operation_list[0]
        stack_bay, stack_row, _, _ = utils.get_pile_split(current_stack['PILE_PLACE'])
        able_pile = None

        state_rule = (current_container['CONTAINER_STATE'] == current_stack['BAY_CONTAINER_STATE'] or current_stack[
            'BAY_CONTAINER_STATE'] is None or current_stack['BAY_CONTAINER_STATE'] == 'MIX') and (
                             current_container['CONTAINER_STATE'] == current_stack['CONTAINER_STATE'] or
                             current_stack[
                                 'CONTAINER_STATE'] is None or current_stack['CONTAINER_STATE'] == 'MIX')
        size_rule = (current_container['CONTAINER_SIZE'] == current_stack['BAY_CONTAINER_SIZE'] or current_stack[
            'BAY_CONTAINER_SIZE'] is None or current_stack['BAY_CONTAINER_SIZE'] == 'MIX') and (
                            current_container['CONTAINER_SIZE'] == current_stack['CONTAINER_SIZE'] or current_stack[
                        'CONTAINER_SIZE'] is None or current_stack['CONTAINER_SIZE'] == 'MIX')

        trade_rule = (current_container['INSIDE_OR_OUTSIDE'] == current_stack['INSIDE_OR_OUTSIDE'] or current_stack[
            'INSIDE_OR_OUTSIDE'] is None or current_stack[
                          'INSIDE_OR_OUTSIDE'] == 'MIX')

        tier_rule = current_stack['NUMS'] < self.options.yard_depth

        disabled_rule = not current_stack['DISABLED'] or (
                current_stack['DISABLED'] and current_stack['BAY_CONTAINER_SIZE'] == 'MIX')

        end_pile_place = f'{self.options.block}{utils.to_double(stack_bay + 2)}{utils.to_double(stack_row)}'

        if current_container['CONTAINER_SIZE'] != 20:
            # if 40ft container, then check the next bay
            # 1. next bay must exist
            # 2. next bay must not have container
            # 3. next bay's bay_container_size must be the same as the current container
            end_pile_place_rule = end_pile_place in list(self.yard_stack_map.keys()) \
                                  and (len([x for x in self.yard_stack_map[end_pile_place]['CONTAINER_LIST'] if x is not None]) == 0) \
                                  and (self.yard_stack_map[end_pile_place][
                                           'BAY_CONTAINER_SIZE'] == current_container['CONTAINER_SIZE'] or
                                       self.yard_stack_map[end_pile_place][
                                           'BAY_CONTAINER_SIZE'] is None)

        else:
            end_pile_place_rule = True
        if state_rule and size_rule and trade_rule and tier_rule and disabled_rule and end_pile_place_rule:
            if disable_stack is not None and disable_stack == current_stack['PILE_PLACE']:
                able_pile = None
            else:
                if current_container['CONTAINER_SIZE'] == 20:
                    able_pile = f'{self.options.block}{utils.to_double(stack_bay)}{utils.to_double(stack_row)}{current_stack["NUMS"] + 1}'
                else:
                    able_pile = f'{self.options.block}{utils.to_double(stack_bay + 1)}{utils.to_double(stack_row)}{current_stack["NUMS"] + 1}'
        return able_pile

    @staticmethod
    def input_policy(able_list, mode):
        # get able pile place mode
        choice_pile_place = None
        if mode == 'random':
            if len(able_list):
                choice_pile_place = choice(able_list)
        return choice_pile_place

    def action_step(self, input_pile=None):
        current_operation = self.operation_list[0]
        step_score = 0
        container_size = int(current_operation['CONTAINER_TYPE'][0:2])

        if current_operation['ACTION'] == 'enter':
            # there are some duplicate data in the operation list
            if current_operation['CONTAINER_REF_ID'] in self.current_container_map:
                return False, 'duplicate', None, None, None, None
            else:
                self.disable_stack = None
                able_pile_place = self.get_able_pile_list()
                if input_pile is not None:
                    input_pile_place = input_pile
                else:
                    input_pile_place = self.input_policy(able_pile_place, 'random')
                if input_pile_place is not None:
                    self.enter_container(input_pile_place)
                    self.action_list.append([None, input_pile_place])
                    self.enter_count += 1

                    final_pile, huge_car_dist, mini_car_dist = utils.count_dist_by_pile_place(self.mc_last_position,
                                                                                              input_pile_place,
                                                                                              current_operation[
                                                                                                  'ACTION'],
                                                                                              self.options)
                    self.mc_last_position = final_pile
                    self.huge_car_dist += huge_car_dist
                    self.mini_car_dist += mini_car_dist

                    step_score += self.count_reward('enter', {
                        'HUGE_CAR_DIST': huge_car_dist,
                        'MINI_CAR_DIST': mini_car_dist,
                        'INPUT_PILE_PLACE': input_pile_place,
                        'CONTAINER_SIZE': current_operation['CONTAINER_SIZE'],
                        'ACTION': current_operation['ACTION']
                    })

                    if self.is_progress:
                        self.update_process()
                    return True, 'enter', step_score, input_pile_place, able_pile_place, None
                else:
                    return False, 'enter', step_score, None, None, None
        elif current_operation['ACTION'] == 'move':
            current_container = self.current_container_map[current_operation['CONTAINER_REF_ID']]
            container_bay, container_row, container_tier, _ = utils.get_pile_split(current_container['PILE_PLACE'])
            able_pile_place = self.get_able_pile_list()
            if input_pile is not None:
                input_pile_place = input_pile
            else:
                input_pile_place = self.input_policy(able_pile_place, 'random')
            if input_pile_place is not None:
                current_container = self.current_container_map[current_operation['CONTAINER_REF_ID']]
                container_bay, container_row, container_tier, _ = utils.get_pile_split(current_container['PILE_PLACE'])
                self.del_container(self.disable_stack, current_container['CONTAINER_REF_ID'], container_tier)

                # from last mc position to the current container position
                final_pile, huge_car_dist, mini_car_dist = utils.count_dist_by_pile_place(self.mc_last_position,
                                                                                          current_container[
                                                                                              'PILE_PLACE'],
                                                                                          current_operation['ACTION'],
                                                                                          self.options)
                self.mc_last_position = final_pile
                self.huge_car_dist += huge_car_dist
                self.mini_car_dist += mini_car_dist

                step_score += self.count_reward('move_leave', {
                    'HUGE_CAR_DIST': huge_car_dist,
                    'MINI_CAR_DIST': mini_car_dist,
                    'REPLACE_TIMES': current_container['REPLACE_TIMES'],
                    'ACTION': current_operation['ACTION']
                })

                self.enter_container(input_pile_place)

                # from the current container position to the target mc position
                final_pile, huge_car_dist, mini_car_dist = utils.count_dist_by_pile_place(self.mc_last_position,
                                                                                          input_pile_place,
                                                                                          current_operation['ACTION'],
                                                                                          self.options)
                self.mc_last_position = final_pile
                self.huge_car_dist += huge_car_dist
                self.mini_car_dist += mini_car_dist

                step_score += self.count_reward('move_enter', {
                    'HUGE_CAR_DIST': huge_car_dist,
                    'MINI_CAR_DIST': mini_car_dist,
                    'INPUT_PILE_PLACE': input_pile_place,
                    'CONTAINER_SIZE': current_operation['CONTAINER_SIZE'],
                    'ACTION': current_operation['ACTION']
                })

                self.action_list.append([current_container['PILE_PLACE'], input_pile_place])
                if self.is_progress:
                    self.update_process()
                return True, 'move', step_score, input_pile_place, able_pile_place, None
            else:
                return False, 'move', step_score, None, None, None
        elif current_operation['ACTION'] == 'leave':
            self.disable_stack = None
            current_container = self.current_container_map[current_operation['CONTAINER_REF_ID']]
            container_bay, container_row, container_tier, _ = utils.get_pile_split(current_container['PILE_PLACE'])
            if container_size == 20:
                current_stack = f'''{self.options.block}{utils.to_double(container_bay)}{utils.to_double(
                    container_row)}'''
            else:
                current_stack = f'''{self.options.block}{utils.to_double(container_bay - 1)}{utils.to_double(
                    container_row)}'''
            current_stack_containers = self.yard_stack_map[current_stack]['CONTAINER_LIST']
            if self.yard_stack_map[current_stack]['NUMS'] == container_tier:
                self.del_container(current_stack, current_container['CONTAINER_REF_ID'], container_tier)
                self.action_list.append([current_container['PILE_PLACE'], None])
                self.leave_count += 1

                final_pile, huge_car_dist, mini_car_dist = utils.count_dist_by_pile_place(self.mc_last_position,
                                                                                          current_container[
                                                                                              'PILE_PLACE'],
                                                                                          current_operation['ACTION'],
                                                                                          self.options)
                self.mc_last_position = final_pile
                self.huge_car_dist += huge_car_dist
                self.mini_car_dist += mini_car_dist

                step_score += self.count_reward('leave', {
                    'HUGE_CAR_DIST': huge_car_dist,
                    'MINI_CAR_DIST': mini_car_dist,
                    'ACTION': current_operation['ACTION']
                })

                if self.is_progress:
                    self.update_process()
                return True, 'leave', step_score, None, None, None
            else:
                # get block container list
                if container_size == 20:
                    self.disable_stack = f'''{self.options.block}{utils.to_double(container_bay)}{utils.to_double(
                        container_row)}'''
                else:
                    self.disable_stack = f'''{self.options.block}{utils.to_double(container_bay - 1)}{utils.to_double(
                        container_row)}'''
                # insert an empty record to solve the recursion problem
                able_pile_place = self.get_able_pile_list()
                self.operation_list.insert(0, {})
                block_container_list = current_stack_containers[container_tier:len(current_stack_containers)]
                block_container_list = list(filter(lambda x: x is not None, block_container_list))
                if self.is_progress:
                    self.add_process_total(len(block_container_list))
                for tem_block_container in block_container_list:
                    block_container = self.current_container_map[tem_block_container['CONTAINER_REF_ID']]
                    block_container['ACTION'] = 'move'
                    block_container['OP_TIME'] = current_operation['OP_TIME']
                    if 'REPLACE_TIMES' in block_container:
                        block_container['REPLACE_TIMES'] += 1
                        self.reload_twice_count += 1
                    else:
                        block_container['REPLACE_TIMES'] = 1
                    self.operation_list.insert(1, block_container)
                self.reload_count += len(block_container_list)

                step_score += self.count_reward('reload', {
                    'REPLACE_TIMES': len(block_container_list),
                    'ACTION': current_operation['ACTION']
                })
                return False, 'leave', step_score, None, able_pile_place, block_container_list

    # when container leave, then delete the container from the stack
    def del_container(self, stack, ref_id, container_tier):
        del self.current_container_map[ref_id]
        self.yard_stack_map[stack]['CONTAINER_LIST'][container_tier - 1] = None

    # when container enter, then add the container to the stack
    def enter_container(self, input_pile_place):
        current_operation = self.operation_list[0]
        current_operation['PILE_PLACE'] = input_pile_place
        self.current_container_map[current_operation['CONTAINER_REF_ID']] = current_operation
        _, _, container_tier, _ = utils.get_pile_split(
            input_pile_place)
        if current_operation['CONTAINER_SIZE'] == 20:
            final_stack = input_pile_place[0:6]
            self.yard_stack_map[final_stack]['CONTAINER_LIST'][container_tier - 1] = current_operation
        elif current_operation['CONTAINER_SIZE'] == 40:
            final_stack = utils.get_forty_size_stack(input_pile_place)
            self.yard_stack_map[final_stack]['CONTAINER_LIST'][container_tier - 1] = current_operation

    def get_reward_r0(self, score_type, score_options=None):
        step_reward = 0
        current_score = 0
        if score_type == 'finish':
            current_score = self.reward_map['finish']
        elif score_type == 'enter':
            current_score = self.reward_map['enter_success']
        elif score_type == 'leave':
            current_score = self.reward_map['leave_success']
        step_reward += current_score
        return step_reward

    def get_reward_r1(self, score_type, score_options=None):
        step_reward = 0
        current_score = 0
        if score_type == 'move_leave':
             current_score = -self.reward_map['relocation_times']
        step_reward += current_score
        return step_reward

    def get_reward_r2(self, score_type, score_options=None):
        step_reward = 0
        current_score = 0
        if score_type in ['enter', 'leave', 'move_leave', 'move_enter']:
            max_w_step = self.options.yard_width - 1
            max_h_step = self.options.yard_height - 1
            current_score += -self.reward_map['huge_car'] * score_options['HUGE_CAR_DIST']
            current_score += -self.reward_map['min_car'] * score_options['MINI_CAR_DIST']
            '''
            if score_options['HUGE_CAR_DIST'] < max_w_step / 4:
                current_score = self.reward_map['huge_car'] * (max_w_step - score_options['HUGE_CAR_DIST'])
            else:
                current_score = -self.reward_map['huge_car'] * score_options['HUGE_CAR_DIST']
            if score_options['MINI_CAR_DIST'] < max_h_step / 2:
                current_score += self.reward_map['min_car'] * (max_w_step - score_options['MINI_CAR_DIST'])
            else:
                current_score += -self.reward_map['min_car'] * score_options['MINI_CAR_DIST']
            '''
            if score_type == 'move_leave' or score_type == 'move_enter':
                if current_score > 0:
                    current_score = -current_score
        step_reward += current_score
        return step_reward

    def get_reward_r3(self, score_type, score_options=None):
        step_reward = 0
        current_score = 0
        if score_type == 'enter' or score_type == 'move_enter':
            # check if cover other container
            container_bay, container_row, container_tier, container_block = utils.get_pile_split(
                score_options['INPUT_PILE_PLACE'])
            cover_num = container_tier - 1
            current_score = self.reward_map['zero_cover_num'] - cover_num
            if 'CONTAINER_SIZE' in score_options:
                current_stack = None
                if score_options['CONTAINER_SIZE'] == 20:
                    current_stack = score_options['INPUT_PILE_PLACE'][0:6]
                elif score_options['CONTAINER_SIZE'] == 40:
                    current_stack = utils.get_forty_size_stack(score_options['INPUT_PILE_PLACE'])
                target_stack = self.yard_stack_map[current_stack]
                target_container_list = target_stack['CONTAINER_LIST']
                if len(target_container_list) - target_container_list.count(None) > 1:
                    # 被压目标箱
                    current_container = self.current_container_map[
                        target_container_list[container_tier - 1]['CONTAINER_REF_ID']]
                    target_container = self.current_container_map[
                        target_container_list[container_tier - 2]['CONTAINER_REF_ID']]
                    if 'REMAIN_DIFF' in target_container:
                        if target_container['REMAIN_DIFF'] > 0:
                            if 'PRE_DIFF' in current_container:
                                current_score += target_container['REMAIN_DIFF'] - current_container['PRE_DIFF']
                        elif target_container['REMAIN_DIFF'] <= 0:
                            y_list = ['Y'] * 8
                            n_list = ['N'] * 2
                            y_list.extend(n_list)
                            expire_diff = choice(y_list)
                            if expire_diff == 'Y':
                                current_score += self.reward_map['cover_expire']
                            elif expire_diff == 'N':
                                current_score += -self.reward_map['cover_expire']
                    else:
                        seven_diff = 7 - target_container['REAL_DIFF']
                        if seven_diff > 0:
                            current_score += -target_container['REAL_DIFF']
                        elif target_container['REAL_DIFF'] > 14:
                            current_score += self.reward_map['long_day'] * 2
                        else:
                            current_score += self.reward_map['long_day']
                    if target_stack['IMPORT_OR_EXPORT'] != current_container['IMPORT_OR_EXPORT']:
                        current_score += -self.reward_map['mix_score']
                    else:
                        current_score += self.reward_map['mix_score']
                    if target_stack['INSIDE_OR_OUTSIDE'] != current_container['INSIDE_OR_OUTSIDE']:
                        current_score += -self.reward_map['mix_score']
                    else:
                        current_score += self.reward_map['mix_score']
                    if current_container['BILL_LADING_REF_ID'] == target_container['BILL_LADING_REF_ID']:
                        current_score += self.reward_map['same_bill_lading']
                    else:
                        current_score += -self.reward_map['same_bill_lading'] / 2
                    current_consignor_list = [bill_lading['CONSIGNOR_NAME'] for bill_lading in
                                              self.container_bill_map[current_container['CONTAINER_REF_ID']]]
                    current_consignor_list = list(dict.fromkeys(current_consignor_list))
                    target_consignor_list = [bill_lading['CONSIGNOR_NAME'] for bill_lading in
                                             self.container_bill_map[target_container['CONTAINER_REF_ID']]]
                    target_consignor_list = list(dict.fromkeys(target_consignor_list))
                    if len(current_consignor_list) == len(target_consignor_list):
                        same_part = list(set(current_consignor_list).intersection(set(target_consignor_list)))
                        if len(same_part) > 0:
                            current_score += self.reward_map['same_party']
                        else:
                            current_score += -self.reward_map['same_party'] / 4
                    else:
                        current_score += -self.reward_map['same_party'] / 2
                    if target_container['IF_BIND'] == 'Y':
                        current_score += -self.reward_map['bind_container']
                    else:
                        current_score += self.reward_map['bind_container']
                    if target_container['IF_BOOK'] == 'Y':
                        current_score += -self.reward_map['book_container']
                    else:
                        current_score += self.reward_map['book_container']
                    if target_container['IF_USED'] == 'Y':
                        current_score += -self.reward_map['used_container']
                    else:
                        current_score += self.reward_map['used_container']
                    if target_container['IF_CHECK'] == 'Y':
                        current_score += -self.reward_map['check_container']
                    else:
                        current_score += self.reward_map['check_container']
                    if target_container['IF_BLOCK'] == 'Y':
                        current_score += self.reward_map['block_container']
                    else:
                        current_score += -self.reward_map['block_container']
                    if target_container['IF_ASSIGN'] == 'Y':
                        current_score += -self.reward_map['assign_container']
                    else:
                        current_score += self.reward_map['assign_container']
            if score_type == 'move_enter':
                # if reload happened, can not add score, minus the score
                if current_score > 0:
                    current_score = -current_score
            step_reward += current_score
        else:
            # if leave success, then add the score
            step_reward += current_score
        return step_reward

    # count action reward
    def count_reward(self, score_type, score_options=None):
        step_reward = 0
        # r0: self.reward_map['finish'], self.reward_map['enter_success'], self.reward_map['leave_success']
        # r1: get_reward_r1
        # r2: get_reward_r2
        # r3: get_reward_r3
        r0 = self.get_reward_r0(score_type, score_options)
        r1 = self.get_reward_r1(score_type, score_options)
        r2 = self.get_reward_r2(score_type, score_options)
        r3 = self.get_reward_r3(score_type, score_options)
        if self.options.train_type == 1:
            # only consider reload times and twice reload times
            step_reward += r0 + r1
        elif self.options.train_type == 2:
            # only consider huge car distance and mini car d
            step_reward += r0 + r2
        elif self.options.train_type == 3:
            step_reward += r0 + r3
        elif self.options.train_type == 4:
            # consider all the factors
            step_reward += r0 + r1 + r2 + r3
        # print(score_type, r0, r1, r2, r3, step_reward)
        self.reward_list.append(step_reward)
        self.total_reward += step_reward
        return step_reward

    def close(self):
        self.game_over = True
        return 0

    def reset(self):
        self.is_progress = True
        self.progress_bar = None
        if self.is_progress:
            self.progress_bar = None
            self.progress_bar_total = 0
            self.progress_bar_current = 0
            self.progress_bar_description = ''
        self.game_over = False
        self.yard_stack_map = {}
        self.current_container_map = {}
        self.container_bill_map = {}
        self.current_time = None
        self.operation_list = []
        self.mc_last_position = None
        self.disable_stack = None
        self.action_list = []
        self.pred_map = {}
        self.cache_bill_map = {}
        self.cache_consignor_map = {}

        self.reload_count = 0
        self.reload_twice_count = 0
        self.leave_count = 0
        self.enter_count = 0
        self.huge_car_dist = 0
        self.mini_car_dist = 0
        self.used_rate = 0
        self.reward_list = []
        self.total_reward = 0
        self.game_over = False

        self.redis = utils.get_redis()
        self.mc_last_position = f'{self.options.block}0101'
        self.update_current_time(self.options.init_time)

    def check_if_had_hang_up_container(self):
        for stack in self.yard_stack_map:
            stack_container_list = self.yard_stack_map[stack]['CONTAINER_LIST']
            if utils.are_non_none_values_consecutive(stack_container_list) is False:
                print(stack, stack_container_list)
                return False
        return True

    def create_yard(self):
        # init yard stack map
        for i in range(1, self.options.yard_width * 2, 2):
            for j in range(1, self.options.yard_height + 1):
                stack_code = f'''{self.options.block}{utils.to_double(i)}{utils.to_double(j)}'''
                self.yard_stack_map[stack_code] = {
                    'PILE_PLACE': stack_code,
                    'CONTAINER_LIST': [None] * self.options.yard_depth,
                    'NUMS': 0,
                    'DISABLED': False
                }
        for ref_id in self.current_container_map:
            container_info = self.current_container_map[ref_id]
            container_bay, container_row, container_tier, _ = utils.get_pile_split(container_info['PILE_PLACE'])
            container_size = container_info['CONTAINER_SIZE']
            if container_size == 20:
                start_pile_place_str = f'{self.options.block}{utils.to_double(container_bay)}{utils.to_double(container_row)}'
                end_pile_place_str = f'{self.options.block}{utils.to_double(container_bay + 2)}{utils.to_double(container_row)}'
            else:
                start_pile_place_str = f'{self.options.block}{utils.to_double(container_bay - 1)}{utils.to_double(container_row)}'
                end_pile_place_str = f'{self.options.block}{utils.to_double(container_bay + 1)}{utils.to_double(container_row)}'
            if start_pile_place_str in self.yard_stack_map:
                start_pile_place = self.yard_stack_map[start_pile_place_str]
                stack_container_list = start_pile_place['CONTAINER_LIST']
                cur_pile_place_container = stack_container_list[container_tier - 1]
                if cur_pile_place_container is None:
                    stack_container_list[container_tier - 1] = container_info
                    start_pile_place['NUMS'] += 1
                else:
                    print('Current position had other container')
                if container_size != 20:
                    for stack_code in self.yard_stack_map.keys():
                        if stack_code[0:4] == end_pile_place_str[0:4]:
                            self.yard_stack_map[stack_code]['DISABLED'] = True
            else:
                print('Current position is not in stack map: ', start_pile_place_str)

        # check if had hang up container
        if not self.check_if_had_hang_up_container():
            print('Some containers are hang up')
        self.update_bay_info()

    def update_bay_info(self):
        self.block_bay_info_map = {}
        for stack in self.yard_stack_map.keys():
            if stack[0:4] not in self.block_bay_info_map:
                self.block_bay_info_map[stack[0:4]] = {
                    'CONTAINER_LIST': [],
                    'CONTAINER_STATE': None,
                    'CONTAINER_SIZE': None,
                }
            self.block_bay_info_map[stack[0:4]]['CONTAINER_LIST'] += list(
                filter(lambda container: container is not None, self.yard_stack_map[stack]['CONTAINER_LIST']))
        for stack in self.block_bay_info_map.values():
            bay_container_size = list(utils.unique_by_container_attr(stack['CONTAINER_LIST'], 'CONTAINER_SIZE').keys())
            bay_container_state = list(
                utils.unique_by_container_attr(stack['CONTAINER_LIST'], 'CONTAINER_STATE').keys())
            if len(bay_container_size) == 0:
                stack['CONTAINER_SIZE'] = None
            elif len(bay_container_size) == 1:
                stack['CONTAINER_SIZE'] = bay_container_size[0]
            elif len(bay_container_size) > 1:
                stack['CONTAINER_SIZE'] = 'MIX'
            if len(bay_container_state) == 0:
                stack['CONTAINER_STATE'] = None
            elif len(bay_container_state) == 1:
                stack['CONTAINER_STATE'] = bay_container_state[0]
            elif len(bay_container_state) > 1:
                stack['CONTAINER_STATE'] = 'MIX'
        for stack in self.yard_stack_map.keys():
            cur_stack = self.yard_stack_map[stack]
            cur_stack['BAY_CONTAINER_SIZE'] = self.block_bay_info_map[stack[0:4]]['CONTAINER_SIZE']
            cur_stack['BAY_CONTAINER_STATE'] = self.block_bay_info_map[stack[0:4]]['CONTAINER_STATE']
            stack_import = utils.unique_by_container_attr(
                filter(lambda container: container is not None, cur_stack['CONTAINER_LIST']),
                'IMPORT_OR_EXPORT')
            stack_trade = utils.unique_by_container_attr(
                filter(lambda container: container is not None, cur_stack['CONTAINER_LIST']),
                'INSIDE_OR_OUTSIDE')
            stack_state = utils.unique_by_container_attr(
                filter(lambda container: container is not None, cur_stack['CONTAINER_LIST']),
                'CONTAINER_STATE')
            stack_size = utils.unique_by_container_attr(
                filter(lambda container: container is not None, cur_stack['CONTAINER_LIST']),
                'CONTAINER_SIZE')
            if len(stack_state) == 0:
                cur_stack['CONTAINER_STATE'] = None
            elif len(stack_state) == 1:
                cur_stack['CONTAINER_STATE'] = list(stack_state.keys())[0]
            elif len(stack_state) > 1:
                cur_stack['CONTAINER_STATE'] = 'MIX'
            if len(stack_size) == 0:
                cur_stack['CONTAINER_SIZE'] = None
            elif len(stack_size) == 1:
                cur_stack['CONTAINER_SIZE'] = list(stack_size.keys())[0]
            elif len(stack_size) > 1:
                cur_stack['CONTAINER_SIZE'] = 'MIX'
            if len(stack_trade) == 0:
                cur_stack['INSIDE_OR_OUTSIDE'] = None
            elif len(stack_trade) == 1:
                cur_stack['INSIDE_OR_OUTSIDE'] = list(stack_trade.keys())[0]
            elif len(stack_trade) > 1:
                cur_stack['INSIDE_OR_OUTSIDE'] = 'MIX'
            if len(stack_import) == 0:
                cur_stack['IMPORT_OR_EXPORT'] = None
            elif len(stack_import) == 1:
                cur_stack['IMPORT_OR_EXPORT'] = list(stack_import.keys())[0]
            elif len(stack_import) > 1:
                cur_stack['IMPORT_OR_EXPORT'] = 'MIX'

    @staticmethod
    def get_map_list():
        map_list = []
        column_list = [
            'CONTAINER_TYPE',
            'INSIDE_OR_OUTSIDE',
            'GOODS_IN_CHINESE',
            'TRANS_TYPE',
            'TYPE_WORK',
            'TOTAL_KINDS_PACKAGE',
            'PAYMENT_CODE',
            'CNTR_ADMIN_CODE',
            'CNTR_OWNER_CODE',
            'PARTY_NAME_PURE'
        ]
        for i in column_list:
            map_list.append({
                'obj': pd.read_excel('../datasets/excel/' + i + '.xlsx'),
                'str': i
            })
        return map_list

    @staticmethod
    def get_map_value(dataframe, key, attr):
        return dataframe.set_index(key)[attr]

    # get predict data by using svr model
    def predict_data(self, pred_dataset):
        count_list = [
            'COUNT',
            'AVG_DIFF',
            'AVG_IN_DIFF',
            'AVG_OUT_DIFF',
            'AVG_REL_DIFF',
            'AVG_DOC_DIFF',
            'AVG_BIND_DIFF',
            'AVG_BOOK_DIFF'
        ]
        drop_list = [
            'CONTAINER_REF_ID',
            'GOODS_IN_CHINESE',
            'TOTAL_KINDS_PACKAGE',
            'CNTR_ADMIN_CODE',
            'CNTR_OWNER_CODE',
            'PARTY_NAME',
            'PORT_MANIFEST_ID',
            'INSIDE_OR_OUTSIDE',
            'BILL_LADING_REF_ID',
            'CONTAINER_NO',
            'PAYMENT_CODE',
            'CONTAINER_TYPE',
            'TRANS_TYPE',
            'TYPE_WORK',
            'PARTY_NAME_PURE',
            'CUSTOMER_NAME',
            'IN_DATE'
        ]
        map_list = self.get_map_list()
        pred_dataset = pred_dataset.copy()
        na_value_map = pd.read_excel('../datasets/excel/MEAN_MAP.xlsx')
        for map_obj in map_list:
            for count_item in count_list:
                map_idx = self.get_map_value(map_obj['obj'], map_obj['str'], count_item)
                pred_dataset[map_obj['str'] + '_' + count_item] = pred_dataset[map_obj['str']].map(map_idx)
                cur_mean = na_value_map[map_obj['str'] + '_' + count_item][0]
                pred_dataset.fillna({map_obj['str'] + '_' + count_item: cur_mean}, inplace=True)
        pred_dataset['IN_DATE'] = pd.to_datetime(pred_dataset['IN_DATE'], format='%Y-%m-%d %H:%M:%S')
        pred_dataset['IN_MONTH'] = pred_dataset['IN_DATE'].dt.month
        pred_dataset['IN_DAY'] = pred_dataset['IN_DATE'].dt.dayofweek
        pred_dataset.fillna({'TOTAL_WEIGHT': 0}, inplace=True)
        pred_dataset = pred_dataset.loc[:, ~pred_dataset.columns.str.contains('Unnamed')]
        pred_dataset.drop_duplicates('CONTAINER_REF_ID', inplace=True)
        src_dataset = pred_dataset
        pred_dataset = pred_dataset.drop(drop_list, axis=1)
        pred_dataset.dropna(inplace=True)
        data_x = np.array(pred_dataset)
        data_columns = np.array(pred_dataset.columns)
        return data_x, data_columns, src_dataset

    # get container bill info
    def get_yard_container_bill_lading(self):
        ref_id_list = list(self.current_container_map.keys())
        future_ref_id_list = [operation['CONTAINER_REF_ID'] for operation in self.operation_list]
        ref_id_list.extend(future_ref_id_list)
        ref_id_list.sort()
        cache_key = utils.get_cache_key({
            'containerRefIds': ref_id_list
        })
        cache_key = f'''bl_{cache_key}'''
        result = self.redis.get(cache_key)
        container_bill_list = json.loads(result)
        return json.dumps(container_bill_list)
        return result

    # init all container info
    def init_yard_container(self):
        cache_key = utils.get_cache_key({
            'd': self.options.init_time
        })
        result = self.redis.get(cache_key)
        result_json = json.loads(result)
        for container in result_json:
            container['CONTAINER_SIZE'] = int(container['CONTAINER_TYPE'][0:2])
            self.current_container_map[container['CONTAINER_REF_ID']] = container

    # get operation list
    def get_operation_list(self):
        ref_id_list = list(self.current_container_map.keys())
        ref_id_list.sort()
        cache_key = utils.get_cache_key({
            'date': self.options.target_time,
            'fixed_date': self.options.init_time
        })
        cache_key = f'''op_{cache_key}'''
        result = self.redis.get(cache_key)
        operation_list = json.loads(result)
        for operation in operation_list:
            if operation['FROM_PILE'] is not None and operation['TO_PILE'] is not None:
                operation['ACTION'] = 'move'
            elif operation['FROM_PILE'] is not None and operation['TO_PILE'] is None:
                operation['ACTION'] = 'leave'
            elif operation['FROM_PILE'] is None and operation['TO_PILE'] is not None:
                operation['ACTION'] = 'enter'
                operation['IN_DATE'] = operation['OP_TIME']
            operation['CONTAINER_SIZE'] = int(operation['CONTAINER_SIZE'])
        self.operation_list = operation_list
        if len(self.operation_list) > 0:
            self.update_current_time(self.operation_list[0]['OP_TIME'])

    def get_yard_container_status(self):
        # 获取集装箱状态信息
        ref_id_list = list(self.current_container_map.keys())
        ref_id_list.sort()
        cache_key = utils.get_cache_key({
            'containerRefIds': ref_id_list,
            'opTime': self.current_time
        })
        cache_key = f'''uc_{cache_key}'''
        result = self.redis.get(cache_key)
        container_status_list = json.loads(result)
        for container_status in container_status_list:
            self.current_container_map[container_status['CONTAINER_REF_ID']] = dict(
                self.current_container_map[container_status['CONTAINER_REF_ID']], **container_status)
        return result


if __name__ == '__main__':
    docker_game_options = DockerGameOptions('01', 16, 15, 4)
    docker_game = DockerGame(docker_game_options)
    docker_game.reset()
    docker_game.create_game()
    while docker_game.game_over is not True:
        docker_game.take_action()
