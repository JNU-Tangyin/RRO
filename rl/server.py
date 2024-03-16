from flask import Flask, jsonify, request
from flask_sockets import Sockets
import json
from docker import DockerGame, DockerGameOptions
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import utils

app = Flask(__name__)
sockets = Sockets(app)

app.config['JSON_AS_ASCII'] = False


@sockets.route('/ws/create_docker_game', websocket=True)
def create_docker_game(ws):
    docker_game = None
    while not ws.closed:
        message = ws.receive()
        if message is None:
            ws.close()
        else:
            message_dict = json.loads(message)
            if message_dict['r_type'] == 'create_game':
                # 初始化堆场信息
                '''
                docker_game_options = DockerGameOptions('01', 16, 15, 4, '2021-08-21 20:46:56', '2021-08-27 23:59:58',
                                                        True, 2, 40)
                docker_game = DockerGame(docker_game_options)
                docker_game.reset()
                docker_game.create_game()
                '''
                docker_game = utils.repair_game()
                ws.send(json.dumps({
                    'code': 0,
                    'message': '现场箱信息',
                    'data': {
                        'init': True,
                        'current_container_map': docker_game.current_container_map,
                        'operation_list': docker_game.operation_list,
                        'container_bill_map': docker_game.container_bill_map,
                        'yard_stack_map': docker_game.yard_stack_map,
                        'game_info': {
                            'current_time': docker_game.current_time,
                            'used_rate': docker_game.used_rate,
                            'reload_count': docker_game.reload_count,
                            'reload_twice_count': docker_game.reload_twice_count,
                            'leave_count': docker_game.leave_count,
                            'enter_count': docker_game.enter_count,
                            'huge_car_dist': docker_game.huge_car_dist,
                            'mini_car_dist': docker_game.mini_car_dist,
                            'mc_last_position': docker_game.mc_last_position,
                            'total_reward': docker_game.total_reward
                        }
                    }
                }, ensure_ascii=False))
            elif message_dict['r_type'] == 'take_action':
                if 'input_pile' in message_dict:
                    action_info = docker_game.take_action(message_dict['input_pile'])
                else:
                    action_info = docker_game.take_action()
                ws.send(json.dumps({
                    'code': 0,
                    'message': '现场箱信息',
                    'data': {
                        'step': True,
                        'current_container_map': docker_game.current_container_map,
                        'operation_list': docker_game.operation_list,
                        'container_bill_map': docker_game.container_bill_map,
                        'yard_stack_map': docker_game.yard_stack_map,
                        'action_info': {
                            'success': action_info[0],
                            'action_type': action_info[1],
                            'score': float(action_info[2]),
                            'pile_place': action_info[3],
                            'step_detail': action_info[6],
                            'able_pile_place': action_info[4],
                            'block_container_id': action_info[5],
                            'enter_able_pile': action_info[7]
                        },
                        'game_info': {
                            'current_time': docker_game.current_time,
                            'used_rate': docker_game.used_rate,
                            'reload_count': docker_game.reload_count,
                            'reload_twice_count': docker_game.reload_twice_count,
                            'leave_count': docker_game.leave_count,
                            'enter_count': docker_game.enter_count,
                            'huge_car_dist': docker_game.huge_car_dist,
                            'mini_car_dist': docker_game.mini_car_dist,
                            'mc_last_position': docker_game.mc_last_position,
                            'total_reward': float(docker_game.total_reward)
                        }
                    }
                }, ensure_ascii=False))


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('', 7788), app, handler_class=WebSocketHandler)
    err = server.serve_forever()
