import pandas as pd
import numpy as np
from plotnine import ggplot, aes, geom_line, geom_ribbon, theme_minimal, ggtitle, labs, stat_smooth
from plotnine_prism import theme_prism
import json


plot_list = [
    {
        'path': '../results/rl/ppo_wp_v4_train_game_status_list_202403031739_{}.txt',
        'nums': 4,
        'label': 'ppo v4 w/ pred'
    },
    {
        'path': '../results/rl/ppo_wop_v4_train_game_status_list_202403031644_{}.txt',
        'nums': 4,
        'label': 'ppo v4 w/o pred'
    },
    {
        'path': '../results/rl/a2c_train_game_status_list_202403041438_{}.txt',
        'nums': 4,
        'label': 'a2c v4 w/ pred'
    }
]

reward_df_list = []
detail_reload_df_list = []
detail_reload_twice_df_list = []
detail_huge_car_list = []
detail_mini_car_list = []


for idx, plot_item in enumerate(plot_list):
    tem_plot_obj_list = []
    for fidx in range(plot_item['nums']):
        file_item = open(plot_item['path'].format(fidx), 'r')
        file_obj = json.loads(file_item.read())
        file_item.close()
        tem_plot_obj_list.append(file_obj)

    window_size = 5
    # reward
    min_plot_obj_len = min([len(plot_obj['total_reward_list']) for plot_obj in tem_plot_obj_list])
    tem_plot_obj_datas = np.array([plot_obj['total_reward_list'][0:min_plot_obj_len] for plot_obj in tem_plot_obj_list])
    tem_plot_obj_mean_rewards = np.mean(tem_plot_obj_datas, axis=0)
    tem_plot_obj_std_rewards = np.std(tem_plot_obj_datas, axis=0)

    tem_plot_df = pd.DataFrame({
        'episode': range(min_plot_obj_len),
        'mean reward': tem_plot_obj_mean_rewards,
        'std reward': tem_plot_obj_std_rewards,
        'algorithm': plot_item['label']
    })

    reward_df_list.append(tem_plot_df)

min_reward_df_len = min([reward_df.shape[0] for reward_df in reward_df_list])
for r_idx, tem_reward_df in enumerate(reward_df_list):
    reward_df = tem_reward_df.head(min_reward_df_len).copy()
    reward_df['mean reward'] = reward_df['mean reward'].rolling(window=window_size, center=True).mean()
    reward_df = reward_df.dropna()

    reward_df['upper'] = reward_df['mean reward'] + reward_df['std reward']
    reward_df['lower'] = reward_df['mean reward'] - reward_df['std reward']
    reward_df_list[r_idx] = reward_df

final_reward_df = pd.concat(reward_df_list)

plot = (ggplot()
        + geom_line(final_reward_df, aes(x='episode', y='mean reward', color='algorithm', fill='algorithm'))
        + labs(x='Episode', y='Reward')
        + geom_ribbon(final_reward_df, aes(x='episode', ymin='lower', ymax='upper', fill='algorithm'), alpha=0.2)
        + theme_prism()
        )

plot.save('../figures/rl/ppo_v4_reward.png')
