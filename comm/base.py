from __future__ import division
import numpy as np
import pandas as pd
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 1000)
import datetime
import time
import os
import copy




# #### 定义获取数据函数

def fix_data(path):
    tmp = pd.read_csv(path, encoding="gbk", engine='python')
    tmp.rename(columns={'Unnamed: 0':'trading_time'}, inplace=True)
    tmp['trading_point'] = pd.to_datetime(tmp.trading_time)
    del tmp['trading_time']
    tmp.set_index(tmp.trading_point, inplace=True)
    return tmp

def High_2_Low(tmp, freq):
    """处理从RiceQuant下载的分钟线数据，
    从分钟线数据合成低频数据
    2017-08-11
    """
    # 分别处理bar数据
    tmp_open = tmp['open'].resample(freq).ohlc()
    tmp_open = tmp_open['open'].dropna()

    tmp_high = tmp['high'].resample(freq).ohlc()
    tmp_high = tmp_high['high'].dropna()

    tmp_low = tmp['low'].resample(freq).ohlc()
    tmp_low = tmp_low['low'].dropna()

    tmp_close = tmp['close'].resample(freq).ohlc()
    tmp_close = tmp_close['close'].dropna()

    tmp_price = pd.concat([tmp_open, tmp_high, tmp_low, tmp_close], axis=1)

    # 处理成交量
    tmp_volume = tmp['volume'].resample(freq).sum()
    tmp_volume.dropna(inplace=True)

    return pd.concat([tmp_price, tmp_volume], axis=1)


def dense_to_one_hot(labels_dense):
    """标签 转换one hot 编码
    输入labels_dense 必须为非负数
    2016-11-21
    """
    num_classes = len(np.unique(labels_dense))  # np.unique 去掉重复函数
    raws_labels = labels_dense.shape[0]
    index_offset = np.arange(raws_labels) * num_classes
    labels_one_hot = np.zeros((raws_labels, num_classes))
    labels_one_hot.flat[index_offset + labels_dense.ravel()] = 1
    return labels_one_hot