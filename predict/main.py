# -- coding: UTF-8 --

import os
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from sklearn.metrics import mean_squared_error
from sklearn import svm
from keras.models import Sequential
from keras.layers import Dense, Dropout
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from keras.models import load_model
import joblib
from dtw import dtw, accelerated_dtw
import math


class DelayTraining:
    def __init__(self):
        self.pred_dataset = None
        self.dataset = None

    def init_dataset(self):
        self.dataset = pd.read_excel('../datasets/excel/CACHE_CLEAN.xlsx')
        data_y = np.array(self.dataset['DIFF'])
        data_x = np.array(self.dataset.drop('DIFF', axis=1))
        data_columns = np.array(self.dataset.columns)
        return data_x, data_y, data_columns

    def init_pred_dataset(self):
        self.pred_dataset = pd.read_excel('../datasets/excel/CACHE_PRE_CLEAN.xlsx')
        src_dataset = pd.read_excel('../datasets/excel/CACHE_PREDICT_PURE.xlsx')
        data_y = np.array(self.pred_dataset['DIFF'])
        data_x = np.array(self.pred_dataset.drop('DIFF', axis=1))
        data_columns = np.array(self.pred_dataset.columns)
        return data_x, data_y, data_columns, src_dataset

    def train_by_lgb(self):
        data_x, data_y, data_columns = self.init_dataset()
        x_train_all, x_predict, y_train_all, y_predict = train_test_split(data_x, data_y, test_size=0.10,
                                                                          random_state=100)
        x_train, x_test, y_train, y_test = train_test_split(x_train_all, y_train_all, test_size=0.2,
                                                            random_state=100)
        train_data = lgb.Dataset(data=x_train, label=y_train)
        test_data = lgb.Dataset(data=x_test, label=y_test)
        num_round = 10
        bst = lgb.train({
            'num_leaves': 2000,
            'learning_rate': 0.01,
            'max_depth': 11,
            'num_trees': 3000,
            'feature_fraction': 0.5,
            'objective': 'regression'
        }, train_data, num_round, valid_sets=[test_data])
        bst.save_model('./model/lgb/lgb_model.txt')
        y_pred = bst.predict(x_predict, num_iteration=bst.best_iteration)
        result = pd.DataFrame({
            'REAL_DIFF': y_predict,
            'PRE_DIFF': y_pred
        })

    def predict_by_lgb(self):
        data_x, data_y, data_columns, source_data = self.init_pred_dataset()
        bst = lgb.Booster(model_file='./model/lgb/lgb_model.txt')
        y_pred = bst.predict(data_x, num_iteration=bst.best_iteration)
        result = pd.DataFrame({
            'CONTAINER_REF_ID': source_data['CONTAINER_REF_ID'],
            'PORT_MANIFEST_ID': source_data['PORT_MANIFEST_ID'],
            'REAL_DIFF': data_y,
            'PRE_DIFF': y_pred
        })
        result = result.loc[~result['REAL_DIFF'].isna()]
        m_list = []
        rate_list = []
        m_df_list = []
        m_id_list = []
        mse_list = []
        dtw_list = []
        for m_id in result['PORT_MANIFEST_ID'].unique():
            m_df = result.loc[result['PORT_MANIFEST_ID'] == m_id]
            m_df = m_df.sort_values(by='REAL_DIFF')
            m_df.reset_index(inplace=True)
            result_of_mse = np.sqrt(mean_squared_error(m_df['REAL_DIFF'], m_df['PRE_DIFF']))
            d, _, _, _ = dtw(m_df['REAL_DIFF'], m_df['PRE_DIFF'], dist=self.manhattan_distance)
            print('********* {} START *********'.format(m_id))
            print('NUMBERS: {}'.format(len(m_df['REAL_DIFF'])))
            print('MSE: {}'.format(result_of_mse))
            print('DTW: {}'.format(d))
            print('********* {} END *********'.format(m_id))
            m_list.append(m_id)
            mse_list.append(result_of_mse)
            rate_list.append(self.get_increase_array(m_df))
            m_df_list.append(m_df)
            dtw_list.append(d)
            m_id_list.append(m_id)
        self.draw_per_img(m_df_list, m_id_list, 'lgb')

        rate_pd = pd.DataFrame({
            'PORT_MANIFEST_ID': m_list,
            'WRONG_RATE': rate_list,
            'MSE_LIST': mse_list,
            'DTW_LIST': dtw_list
        })

        print(rate_pd.describe())

        rate_pd.to_excel('../results/lgb/WRONG_RATE.xlsx')
        result.to_excel('./results/lgb/PRE_RESULT.xlsx')

    def train_by_svm(self):
        data_x, data_y, source_columns = self.init_dataset()
        x_train_all, x_predict, y_train_all, y_predict = train_test_split(data_x, data_y, test_size=0.10,
                                                                          random_state=100)
        x_train, x_test, y_train, y_test = train_test_split(x_train_all, y_train_all, test_size=0.2,
                                                            random_state=100)
        clf = svm.SVR(kernel='rbf', C=6.0)
        clf.fit(x_train, y_train)
        joblib.dump(clf, './model/svm/svr_model.pkl')

    def predict_by_svm(self):
        p_data_x, p_data_y, predict_columns, source_data = self.init_pred_dataset()
        clf = joblib.load('./model/svm/svr_model.pkl')
        y_pred = clf.predict(p_data_x)
        result = pd.DataFrame({
            'CONTAINER_REF_ID': source_data['CONTAINER_REF_ID'],
            'PORT_MANIFEST_ID': source_data['PORT_MANIFEST_ID'],
            'REAL_DIFF': p_data_y,
            'PRE_DIFF': y_pred
        })
        result = result.loc[~result['REAL_DIFF'].isna()]
        m_list = []
        rate_list = []
        m_df_list = []
        m_id_list = []
        mse_list = []
        dtw_list = []
        for m_id in result['PORT_MANIFEST_ID'].unique():
            m_df = result.loc[result['PORT_MANIFEST_ID'] == m_id]
            m_df = m_df.sort_values(by='REAL_DIFF')
            m_df.reset_index(inplace=True)
            result_of_mse = np.sqrt(mean_squared_error(m_df['REAL_DIFF'], m_df['PRE_DIFF']))
            d, _, _, _ = dtw(m_df['REAL_DIFF'], m_df['PRE_DIFF'], dist=self.manhattan_distance)
            print('********* SHIP [{}] START *********'.format(m_id))
            print('NUMBERS: {}'.format(len(m_df['REAL_DIFF'])))
            print('MSE: {}'.format(result_of_mse))
            print('DTW: {}'.format(d))
            print('********* SHIP [{}] END *********'.format(m_id))
            m_list.append(m_id)
            rate_list.append(self.get_increase_array(m_df))
            m_df_list.append(m_df)
            dtw_list.append(d)
            m_id_list.append(m_id)
            mse_list.append(result_of_mse)
        self.draw_per_img(m_df_list, m_id_list, 'svm')

        rate_pd = pd.DataFrame({
            'PORT_MANIFEST_ID': m_list,
            'WRONG_RATE': rate_list,
            'MSE_LIST': mse_list,
            'DTW_LIST': dtw_list
        })

        rate_pd.to_excel('../results/svm/WRONG_RATE.xlsx')
        result.to_excel('../results/svm/PRE_RESULT.xlsx')

    def train_by_bp(self):
        data_x, data_y, data_columns = self.init_dataset()
        x_train_all, x_predict, y_train_all, y_predict = train_test_split(data_x, data_y, test_size=0.10,
                                                                          random_state=100)
        x_train, x_test, y_train, y_test = train_test_split(x_train_all, y_train_all, test_size=0.2,
                                                            random_state=100)
        model = Sequential()
        model.add(Dense(units=100,
                        activation='relu',
                        input_shape=(x_train.shape[1],)
                        )
                  )
        model.add(Dropout(0.2))
        model.add(Dense(units=80,
                        activation='relu'
                        )
                  )
        model.add(Dense(units=1,
                        activation='linear'
                        )
                  )

        model.compile(loss='mse',
                      optimizer='adam',
                      )
        model.fit(x_train, y_train,
                            epochs=1000,
                            batch_size=100,
                            verbose=2,
                            validation_data=(x_test, y_test)
                            )
        # 保存模型
        model.save('./model/bp/model_MLP.h5')

    def predict_by_bp(self):
        p_data_x, p_data_y, data_columns, source_data = self.init_pred_dataset()

        # 加载模型
        model = load_model('./model/bp/model_MLP.h5')
        y_pred_list = model.predict(p_data_x)
        y_pred = []
        for i in y_pred_list:
            y_pred.append(i[0])

        result = pd.DataFrame({
            'CONTAINER_REF_ID': source_data['CONTAINER_REF_ID'],
            'PORT_MANIFEST_ID': source_data['PORT_MANIFEST_ID'],
            'REAL_DIFF': p_data_y,
            'PRE_DIFF': y_pred
        })
        m_list = []
        rate_list = []
        m_df_list = []
        m_id_list = []
        mse_list = []
        dtw_list = []
        for m_id in result['PORT_MANIFEST_ID'].unique():
            m_df = result.loc[result['PORT_MANIFEST_ID'] == m_id]
            m_df = m_df.sort_values(by='REAL_DIFF')
            m_df.reset_index(inplace=True)
            result_of_mse = np.sqrt(mean_squared_error(m_df['REAL_DIFF'], m_df['PRE_DIFF']))
            d, _, _, _ = dtw(m_df['REAL_DIFF'], m_df['PRE_DIFF'], dist=self.manhattan_distance)
            print('********* {} START *********'.format(m_id))
            print('NUMBERS: {}'.format(len(m_df['REAL_DIFF'])))
            print('MSE: {}'.format(result_of_mse))
            print('DTW: {}'.format(d))
            print('********* {} END *********'.format(m_id))
            m_list.append(m_id)
            mse_list.append(result_of_mse)
            dtw_list.append(d)
            rate_list.append(self.get_increase_array(m_df))
            m_df_list.append(m_df)
            m_id_list.append(m_id)
        self.draw_per_img(m_df_list, m_id_list, 'bp')

        rate_pd = pd.DataFrame({
            'PORT_MANIFEST_ID': m_list,
            'WRONG_RATE': rate_list,
            'MSE_LIST': mse_list,
            'DTW_LIST': dtw_list
        })

        rate_pd.to_excel('../results/bp/WRONG_RATE.xlsx')
        result.to_excel('../results/bp/PRE_RESULT.xlsx')

    @staticmethod
    def manhattan_distance(x, y):
        return np.abs(x - y)

    @staticmethod
    def draw_per_img(m_df_list, m_id_list, i_type):
        fig = plt.figure(figsize=(14, 400))
        row_num = math.ceil(len(m_df_list) / 2)
        count_num = 0
        for idx in range(0, len(m_df_list)):
            count_num += 1
            m_df = m_df_list[idx]
            plt.plot(m_df.index.values, m_df['REAL_DIFF'])
            plt.plot(m_df.index.values, m_df['PRE_DIFF'])
            plt.rcParams['axes.unicode_minus'] = False
            plt.xlabel('Container pickup sequence')
            plt.ylabel('Stacking days')
            plt.legend(['Ground Truth', 'Predicted'], loc='upper left')
            plt.grid()
            plt.sca(plt.subplot(row_num, 2, count_num))
        plt.savefig('../figures/predict/' + i_type + '/total.jpg')
        plt.close()

    @staticmethod
    def get_increase_array(df):
        rel_diff = df['PRE_DIFF'].tolist()
        arr = []
        low_count = 0
        for i in range(0, len(rel_diff)):
            item = rel_diff[i]
            if i == 0:
                arr.append(item)
            else:
                prev_item = rel_diff[i - 1]
                if prev_item < item:
                    arr.append(item)
                else:
                    low_count = low_count + 1
        low_rate = low_count / len(rel_diff)
        return low_rate


if __name__ == '__main__':
    delay_training = DelayTraining()
    delay_training.train_by_svm()
    delay_training.predict_by_svm()
    delay_training.train_by_lgb()
    delay_training.predict_by_lgb()
    delay_training.train_by_bp()
    delay_training.predict_by_bp()
