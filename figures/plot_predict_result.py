import pandas as pd
import numpy as np
from plotnine import * # ggplot, aes, geom_line, geom_point, labs, theme_classic
from plotnine_prism import theme_prism
import random

npg = ["#E64B35CC","#4DBBD5CC","#00A087CC", "#3C5488CC", "#F39B7FCC", "#8491B4CC", "#91D1c2CC","#DC0000CC", "#7E6148CC"]
bp_df = pd.read_excel('../results/bp/PRE_RESULT.xlsx', index_col=0)
lgb_df = pd.read_excel('../results/lgb/PRE_RESULT.xlsx', index_col=0)
svm_df = pd.read_excel('../results/svm/PRE_RESULT.xlsx', index_col=0)

unique_manifest = list(set(bp_df['PORT_MANIFEST_ID']))

manifest_id = random.choice(unique_manifest)

port_svm_df = svm_df[svm_df['PORT_MANIFEST_ID'] == manifest_id].copy()
port_lgb_df = lgb_df[lgb_df['PORT_MANIFEST_ID'] == manifest_id].copy()
port_bp_df = bp_df[bp_df['PORT_MANIFEST_ID'] == manifest_id].copy()

# Consistency between predicted and actual container retrieval sequences
port_svm_pre_diff_list = list(port_svm_df['PRE_DIFF'])
port_lgb_pre_diff_list = list(port_lgb_df['PRE_DIFF'])
port_bp_pre_diff_list = list(port_bp_df['PRE_DIFF'])
not_sequences_list = []
for idx, row in enumerate(port_svm_pre_diff_list):
    if idx > 0:
        cur_row = row
        pre_row = port_svm_pre_diff_list[idx - 1]
        if cur_row < pre_row:
            not_sequences_list.append(idx)

port_svm_df['episode'] = range(len(port_svm_pre_diff_list))
port_svm_df['algorithm'] = ['Predicted' for _ in range(len(port_svm_pre_diff_list))]

port_svm_real_df = port_svm_df.copy()
port_svm_real_df['algorithm'] = ['Real' for _ in range(len(port_svm_pre_diff_list))]

port_lgb_df['episode'] = range(len(port_lgb_pre_diff_list))
port_bp_df['episode'] = range(len(port_bp_pre_diff_list))

not_sequences_df = pd.DataFrame({
    'episode': not_sequences_list,
    'diff': [port_svm_pre_diff_list[i] for i in not_sequences_list]
})

plot = (
    ggplot()
    + geom_line(port_svm_df, aes(x='episode', y='PRE_DIFF', color='algorithm', fill='algorithm'), size = 1)
    + geom_line(port_svm_real_df, aes(x='episode', y='REAL_DIFF', color='algorithm', fill='algorithm'), size = 1)
    + geom_point(not_sequences_df, aes(x='episode', y='diff'), size=6, fill=None, alpha=0.2)
    + labs(x='Container pickup sequence', y='#Stacking days')
    + scale_fill_manual(values=npg)
    + scale_color_manual(values=npg)
    + theme_prism()
    + theme(legend_position=(0.2,0.8))
)

plot.save('../figures/rl/consistency_between_predicted_and_actual_container_retrieval_sequences.pdf')

port_svm_df['algorithm'] = ['svr' for _ in range(len(port_svm_pre_diff_list))]
port_lgb_df['algorithm'] = ['lightGBM' for _ in range(len(port_lgb_pre_diff_list))]
port_bp_df['algorithm'] = ['bp' for _ in range(len(port_bp_pre_diff_list))]

concat_df = pd.concat([port_svm_df, port_lgb_df, port_bp_df])

compet_plot = (
    ggplot()
    + geom_line(concat_df, aes(x='episode', y='PRE_DIFF', color='algorithm', fill='algorithm'), size = 1)
    + geom_line(port_svm_real_df, aes(x='episode', y='REAL_DIFF', color='algorithm', fill='algorithm'), linetype='dashed', size = 1)
    + labs(x='Container pickup sequence', y='#Stacking days')
    + scale_fill_manual(values=npg)
    + scale_color_manual(values=npg)
    + theme_prism()
    + theme(legend_position=(.2,.8))
)

compet_plot.save('../figures/rl/comparison_of_prediction_accuracy_of_different_methods.pdf')
