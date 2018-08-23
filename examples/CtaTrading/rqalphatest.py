# encoding: UTF-8
from __future__ import  print_function
import  numpy as np
import bcolz
import json
from time import  time
from datetime import datetime
from  cyvn.trader.app.ctaStrategy.ctaBase import DAILY_DB_NAME

def getcvs():
    import  os
    os.getcwd()
    with open("/home/linlin/.rqalpha/bundle/futures.bcolz/__attrs__") as f:
        drSetting = json.load(f)
    if 'line_map' in drSetting:
                    lm= drSetting['line_map']
                    if 'RB88' in lm:
                        lines = lm['RB88']
    data = bcolz.open(rootdir="/home/linlin/.rqalpha/bundle/futures.bcolz", mode='a')
    save = data.todataframe(columns= ['date', 'open', 'close','high', 'low', 'volume','open_interest'])
    s = save.iloc[lines[0]:lines[1]]
    s.to_csv('futures.cvs')


def loadDayTxt(fileName, dbName, symbol):
    """将Multicharts导出的csv格式的历史数据插入到Mongo数据库中"""
    import csv
    import pandas as pd
    import pymongo

    from cyvn.trader.vtObject import VtBarData

    getcvs()

    start = time()
    print (u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol))

    # 锁定集合，并创建索引


    client = pymongo.MongoClient('149.28.56.155',
                                            27017,
                                            username = 'root',
                                            password = 'll159582',
                                            connectTimeoutMS=500)
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库

    reader = csv.DictReader(open(fileName, 'r',))
    rows = [row for row in reader]
    for d in rows[-200:-1]:
        bar = VtBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.exchange = 'SHFE'
        bar.gatewayName = 'CTP'
        bar.open = float(d['open'])/10000
        bar.high = float(d['high'])/10000
        bar.low = float(d['low'])/10000
        bar.close = float(d['close'])/10000
        bar.date = datetime.strptime(d['date'], '%Y%m%d').strftime('%Y%m%d')
        bar.time = "15:00"
        bar.datetime = datetime.strptime(bar.date, '%Y%m%d')
        bar.volume = d['volume']
        bar.openInterest = d['open_interest']

        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)
        print(bar.date)


    print (u'插入完毕，耗时：%s' % (time()-start))


if __name__ == '__main__':
    loadDayTxt('futures.cvs', DAILY_DB_NAME, 'rb1901')