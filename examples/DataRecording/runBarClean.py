#encoding: UTF-8
import json
from datetime import datetime, timedelta, time

from pymongo import MongoClient
from cyvn.trader.vtConstant import *
from cyvn.trader.vtObject import VtBarData
from cyvn.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME, MINUTE_DB_NAME

MORNING_START = time(9, 0)
MORNING_REST = time(10, 15)
MORNING_RESTART = time(10, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 30)
AFTERNOON_END = time(15, 15)
NIGHT_START = time(21, 0)
NIGHT_END = time(2,30)

NIGHT_MARKET_DICT = {}
NIGHT_MARKET_DICT['SHF1'] = ('rb','ru','hc','bu')
NIGHT_MARKET_DICT['SHF2'] = ('cu','al','zn','pb','sn','ni')
NIGHT_MARKET_DICT['SHF3'] = ('au','ag','sc')
NIGHT_MARKET_DICT['DCE'] = ('p','j','m','y','a','b','jm','i')
NIGHT_MARKET_DICT['CZC'] = ('SR','CF','RM','MA','TA','ZC','FG','OI','CY')
NIGHT_MARKET_ALL = NIGHT_MARKET_DICT['SHF1']+NIGHT_MARKET_DICT['SHF2']+NIGHT_MARKET_DICT['SHF3']+NIGHT_MARKET_DICT['DCE']+NIGHT_MARKET_DICT['CZC']

MARKET_STOCK_INDEX= ('IF','IH','IC')
MARKET_BOND = ('T','TF')

#----------------------------------------------------------------------
def convertBar(collectionName, tickDb, barDb):
    """处理数据"""
    # 处理夜盘收盘的分钟线问题
    nonum_name = filter(str.isalpha, str(collectionName))
    today = datetime.now()
    yesterday = today - timedelta(1) # 昨天
    startTime = None

    """夜盘处理（凌晨时间处理）"""
    if today.time() > NIGHT_END and today.time() < time(11,0):
        if nonum_name in NIGHT_MARKET_DICT['SHF1']:
            # 23:00结束合约
            start = yesterday
            startTime = start.replace(hour=22, minute=59,
                          second=0, microsecond=0)
        elif nonum_name in NIGHT_MARKET_DICT['SHF2']:
            # 01:00结束合约
            start = today   # 今天
            startTime = start.replace(hour=0, minute=59,
                          second=0, microsecond=0)
        elif nonum_name in NIGHT_MARKET_DICT['SHF3']:
            # 02:30结束合约
            start = today   # 今天
            startTime = start.replace(hour=2, minute=29,
                          second=0, microsecond=0)
        elif (nonum_name in NIGHT_MARKET_DICT['DCE'] or
              nonum_name in NIGHT_MARKET_DICT['CZC']):
            # 23:30结束合约
            start = yesterday   # 昨天
            startTime = start.replace(hour=23, minute=29,
                          second=0, microsecond=0)
        else:
            # 其他合约夜盘不做处理
            startTime = None

    """白天收盘处理"""
    if today.time() > AFTERNOON_END and today.time() < NIGHT_START:
        if nonum_name in MARKET_BOND:
            start = today   # 今天
            startTime = start.replace(hour=15, minute=14,
                          second=0, microsecond=0)
        else:
            start = today   # 今天
            startTime = start.replace(hour=14, minute=59,
                          second=0, microsecond=0)

    if startTime:
        mc = MongoClient('localhost', 27017)    # 创建MongoClient
        cl = mc[tickDb][collectionName]         # 获取tick数据集合
        d = {'datetime':{'$gte':startTime}}     # 只过滤从start开始的数据
        cx = cl.find(d).sort('datetime')        # 获取数据指针
        lastTime = startTime - timedelta(minutes=1)
        lastTick = None
        # 获取上一个tick
        d = {'datetime':{'$gte':lastTime,'$lt':startTime}}
        lastData = cl.find(d).sort('datetime')       # 获取数据指针
        for i in lastData:
            lastTick = i
        # 遍历数据
        bar = None
        for tick in cx:
            # 转换tick数据为bar数据
            if not bar:
                bar = VtBarData()
                #dt = data['datetime'].time()
                bar.vtSymbol = tick['vtSymbol']
                bar.symbol = tick['symbol']
                bar.exchange = tick['exchange']

                bar.open = tick['lastPrice']
                bar.high = tick['lastPrice']
                bar.low = tick['lastPrice']
            else:
                bar.high = max(bar.high, tick['lastPrice'])
                bar.low = min(bar.low, tick['lastPrice'])
            # 通用更新部分
            bar.close = tick['lastPrice']
            bar.datetime = tick['datetime']
            bar.openInterest = tick['openInterest']

            if lastTick:
                bar.volume += (tick['volume'] - lastTick['volume']) # 当前K线内的成交量

            # 缓存Tick
            lastTick = tick
        # 转换bar时间戳,考虑可能节假日启动程序，但是没有收盘tick
        if bar:
            bar.datetime = startTime # 使用目标的时间日期
            bar.date = bar.datetime.strftime('%Y%m%d')
            bar.time = bar.datetime.strftime('%H:%M:%S.%f')
            # 更新到bar数据库
            flt = {'datetime': bar.datetime}
            clBar = mc[barDb][collectionName]
            clBar.update_one(flt, {'$set':bar.__dict__}, upsert=True)
            # 重置bar
            bar = None
            print (u'分钟线处理完成，数据库：%s, 集合：%s' %(barDb, collectionName))
#----------------------------------------------------------------------
def barCleaning():
    """运行收盘最后一分钟数据清洗"""
    print (u'开始处理最后一分钟数据')

    # 加载配置
    setting = {}
    with open("DR_setting.json") as f:
        drSetting = json.load(f)
    l = drSetting['tick']
    for s in l:
        symbol = s[0]
        #cleanData(TICK_DB_NAME, symbol, start)
        convertBar(symbol, TICK_DB_NAME, MINUTE_DB_NAME)

    print (u'收盘前最后一分钟数据处理工作完成')
if name == 'main':
    barCleaning()