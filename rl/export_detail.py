import pandas as pd
import numpy as np
from plotnine import ggplot, aes, geom_line, geom_ribbon, theme_minimal, ggtitle, labs, stat_smooth
from plotnine_prism import theme_prism
import json

plot_list = [
    {
        'path': '../results/rl/ppo_wp_v4_train_game_status_list_202403181909_{}.txt',
        'nums': 4,
        'label': 'ppo v4 w/ pred',
        'full_label': 'PPO with prediction'
    },
    {
        'path': '../results/rl/ppo_wop_v4_train_game_status_list_202403181809_{}.txt',
        'nums': 4,
        'label': 'ppo v4 w/o pred',
        'full_label': 'PPO without prediction'
    }
]

detail_df_list = []
detail_df_huge_car_list = []
detail_reload_df_list = []
detail_reload_twice_df_list = []
detail_huge_car_list = []
detail_mini_car_list = []

full_label_list = ['Human']
mean_reload_list = [244]
mean_reload_rate_list = [95.6]
mean_move_distance_list = ['Not available']

for idx, plot_item in enumerate(plot_list):
    tem_plot_obj_list = []
    for fidx in range(0, plot_item['nums']):
        file_item = open(plot_item['path'].format(fidx), 'r')
        file_obj = json.loads(file_item.read())
        file_item.close()
        tem_plot_obj_list.append(file_obj)

    window_size = 5
    # detail
    tem_detail_plot_list = []
    for plot_obj in tem_plot_obj_list:
        tem_op_map = {}
        for detail_item in plot_obj['total_detail_list']:
            total_op_nums = detail_item[3] + detail_item[5]
            if total_op_nums not in tem_op_map:
                tem_op_map[total_op_nums] = {
                    'reload_count': [],
                    'reload_twice_count': [],
                    'huge_car_dist': [],
                    'mini_car_dist': [],
                    'reload_rate': []
                }
            tem_op_map[total_op_nums]['reload_count'].append(detail_item[1])
            tem_op_map[total_op_nums]['reload_twice_count'].append(detail_item[2])
            tem_op_map[total_op_nums]['reload_rate'].append(detail_item[4])
            tem_op_map[total_op_nums]['huge_car_dist'].append(detail_item[6])
            tem_op_map[total_op_nums]['mini_car_dist'].append(detail_item[7])

        max_total_op_nums = max(tem_op_map.keys())
        tem_detail_plot_list.append(tem_op_map[max_total_op_nums])

    min_plot_obj_len = min([len(plot_obj['reload_count']) for plot_obj in tem_detail_plot_list])

    full_label_list.append(plot_item['full_label'])
    mean_reload = np.mean([np.mean(detail_item['reload_count']) for detail_item in tem_detail_plot_list])
    mean_reload_rate = np.mean([np.mean(detail_item['reload_rate']) for detail_item in tem_detail_plot_list])
    mean_distance = np.mean([np.mean(detail_item['huge_car_dist']) for detail_item in tem_detail_plot_list])
    mean_reload_list.append(mean_reload)
    mean_reload_rate_list.append(mean_reload_rate)
    mean_move_distance_list.append(mean_distance)

    min_plot_obj_len = min([len(plot_obj['reload_count']) for plot_obj in tem_detail_plot_list])

    # reload
    tem_plot_obj_datas = np.array(
        [plot_obj['reload_count'][0:min_plot_obj_len] for plot_obj in tem_detail_plot_list])
    tem_plot_obj_mean_rewards = np.mean(tem_plot_obj_datas, axis=0)
    tem_plot_obj_std_rewards = np.std(tem_plot_obj_datas, axis=0)

    tem_plot_df = pd.DataFrame({
        'episode': range(min_plot_obj_len),
        'mean detail': tem_plot_obj_mean_rewards,
        'std detail': tem_plot_obj_std_rewards,
        'algorithm': plot_item['label']
    })

    detail_df_list.append(tem_plot_df)

    # huge
    tem_plot_obj_datas = np.array(
        [plot_obj['huge_car_dist'][0:min_plot_obj_len] for plot_obj in tem_detail_plot_list])
    tem_plot_obj_mean_rewards = np.mean(tem_plot_obj_datas, axis=0)
    tem_plot_obj_std_rewards = np.std(tem_plot_obj_datas, axis=0)

    tem_plot_df = pd.DataFrame({
        'episode': range(min_plot_obj_len),
        'mean detail': tem_plot_obj_mean_rewards,
        'std detail': tem_plot_obj_std_rewards,
        'algorithm': plot_item['label']
    })

    detail_df_huge_car_list.append(tem_plot_df)

min_detail_df_len = min([detail_df.shape[0] for detail_df in detail_df_list])
for d_idx, detail_df in enumerate(detail_df_list):
    detail_df = detail_df.head(min_detail_df_len).copy()
    detail_df['mean detail'] = detail_df['mean detail'].rolling(window=window_size, center=True).mean()
    detail_df = detail_df.dropna()

    detail_df['upper'] = detail_df['mean detail'] + detail_df['std detail']
    detail_df['lower'] = detail_df['mean detail'] - detail_df['std detail']
    detail_df_list[d_idx] = detail_df

for d_idx, detail_df in enumerate(detail_df_huge_car_list):
    detail_df = detail_df.head(min_detail_df_len).copy()
    detail_df['mean detail'] = detail_df['mean detail'].rolling(window=window_size, center=True).mean()
    detail_df = detail_df.dropna()

    detail_df['upper'] = detail_df['mean detail'] + detail_df['std detail']
    detail_df['lower'] = detail_df['mean detail'] - detail_df['std detail']
    detail_df_huge_car_list[d_idx] = detail_df

final_detail_df = pd.concat(detail_df_list)
final_detail_huge_car_df = pd.concat(detail_df_huge_car_list)

# data table
data_table = pd.DataFrame({
    'Algorithm': full_label_list,
    'Relocated containers': mean_reload_list,
    'Relocation rate (%)': mean_reload_rate_list,
    'Moving distance *': mean_move_distance_list
})

data_table.to_csv('../results/rl/detail_compare.csv', index=False)
