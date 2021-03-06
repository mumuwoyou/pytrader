# encoding: UTF-8

'''
本文件中实现了行情数据记录引擎，用于汇总TICK数据，并生成K线插入数据库。

使用DR_setting.json来配置需要收集的合约，以及主力合约代码。
'''

import json
import csv
import os
import copy
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta, time
from queue import Queue, Empty
from threading import Thread
from pymongo.errors import DuplicateKeyError

from cyvn.trader.eventEngine import Event
from cyvn.trader.vtEvent import *
from cyvn.trader.vtFunction import todayDate, getJsonPath
from cyvn.trader.vtObject import VtSubscribeReq, VtLogData, VtBarData, VtTickData


from .drBase import *
from .language import text



########################################################################
#期货交易时间段
MORNING_START = time(8, 59)
MORNING_REST = time(10, 15)
MORNING_RESTART = time(10, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 30)
AFTERNOON_END = time(15, 16)
NIGHT_START = time(20, 59)
NIGHT_END = time(2, 30)




class DrEngine(object):
    """数据记录引擎"""
    
    settingFileName = 'DR_setting.json'
    settingFilePath = getJsonPath(settingFileName, __file__)  

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = todayDate()
        
        # 主力合约代码映射字典，key为具体的合约代码（如IF1604），value为主力合约代码（如IF0000）
        self.activeSymbolDict = {}
        
        # Tick对象字典
        self.tickSymbolSet = set()

        self.barSymbolSet = set()

        # K线合成器字典
        self.bmDict = {}

        # 配置字典
        self.settingDict = OrderedDict()
        
        # 负责执行数据库插入的单独线程相关
        self.active = False                     # 工作状态
        self.queue = Queue()                    # 队列
        self.thread = Thread(target=self.run)   # 线程
        
        # 载入设置，订阅行情
        #self.loadSetting()
        
        # 启动数据插入线程
        self.start()
    
        # 注册事件监听
        self.registerEvent()  
    
    #----------------------------------------------------------------------
    def loadSetting(self):
        """加载配置"""
        with open(self.settingFilePath) as f:
            drSetting = json.load(f)

            # 如果working设为False则不启动行情记录功能
            working = drSetting['working']
            if not working:
                return

            # Tick记录配置
            if 'tick' in drSetting:
                l = drSetting['tick']

                for setting in l:
                    symbol = setting[0]
                    gateway = setting[1]
                    vtSymbol = symbol

                    req = VtSubscribeReq()
                    req.symbol = setting[0]

                    # 针对LTS和IB接口，订阅行情需要交易所代码
                    if len(setting)>=3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])

                    # 针对IB接口，订阅行情需要货币和产品类型
                    if len(setting)>=5:
                        req.currency = setting[3]
                        req.productClass = setting[4]

                    self.mainEngine.subscribe(req, gateway)

                    #tick = VtTickData()           # 该tick实例可以用于缓存部分数据（目前未使用）
                    #self.tickDict[vtSymbol] = tick

                    self.tickSymbolSet.add(vtSymbol)
                    
                    # 保存到配置字典中
                    if vtSymbol not in self.settingDict:
                        d = {
                            'symbol': symbol,
                            'gateway': gateway,
                            'tick': True
                        }
                        self.settingDict[vtSymbol] = d
                    else:
                        d = self.settingDict[vtSymbol]
                        d['tick'] = True

            # 分钟线记录配置
            if 'bar' in drSetting:
                l = drSetting['bar']

                for setting in l:
                    symbol = setting[0]
                    gateway = setting[1]
                    vtSymbol = symbol

                    req = VtSubscribeReq()
                    req.symbol = symbol                    

                    if len(setting)>=3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])

                    if len(setting)>=5:
                        req.currency = setting[3]
                        req.productClass = setting[4]                    

                    self.mainEngine.subscribe(req, gateway)  

                    self.barSymbolSet.add(vtSymbol)
                    # 保存到配置字典中
                    if vtSymbol not in self.settingDict:
                        d = {
                            'symbol': symbol,
                            'gateway': gateway,
                            'bar': True
                        }
                        self.settingDict[vtSymbol] = d
                    else:
                        d = self.settingDict[vtSymbol]
                        d['bar'] = True     
                        
                    # 创建BarManager对象
                    #self.bmDict[vtSymbol] = BarGenerator(self.onBar)
                    self.bmDict[vtSymbol] = RecorderBarManager(self.onBar, self.onXBar)

            # 主力合约记录配置
            if 'active' in drSetting:
                d = drSetting['active']
                self.activeSymbolDict = {vtSymbol:activeSymbol for activeSymbol, vtSymbol in d.items()}
    
    #----------------------------------------------------------------------
    def getSetting(self):
        """获取配置"""
        return self.settingDict, self.activeSymbolDict

    #----------------------------------------------------------------------
    def procecssTickEvent(self, event):
        """处理行情事件"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol
        
        # 生成datetime对象
        if not tick.datetime:
            tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S')

        self.onTick(tick)
        
        bm = self.bmDict.get(vtSymbol, None)
        if bm:
            bm.updateTick(tick)

    def isDirtyData(self,tick):
        """ 判断脏数据 """

        #期货判断交易时间
        dt = datetime.now().time()

        # 如果在交易事件内，则为有效数据，无需清洗
        if ((MORNING_START <= dt < MORNING_REST) or
            (MORNING_RESTART <= dt < MORNING_END) or
            (AFTERNOON_START <= dt < AFTERNOON_END) or
            (dt >= NIGHT_START) or
            (dt < NIGHT_END)):
            return False

        #中间启停去掉脏数据
        if not tick.datetime:
            tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S')

            #判断脏数据
            time_now = datetime.now()
            time_delt = (tick.datetime - time_now).total_seconds()

            if time_delt < 180 and  time_delt > -180: #大于3分钟 脏数据
                return False

        return True
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        vtSymbol = tick.vtSymbol
        
        if vtSymbol in self.tickSymbolSet:
            self.insertData(TICK_DB_NAME, vtSymbol, tick)
            
            if vtSymbol in self.activeSymbolDict:
                activeSymbol = self.activeSymbolDict[vtSymbol]
                self.insertData(TICK_DB_NAME, activeSymbol, tick)
            
            
            self.writeDrLog(text.TICK_LOGGING_MESSAGE.format(symbol=tick.vtSymbol,
                                                             time=tick.time, 
                                                             last=tick.lastPrice, 
                                                             bid=tick.bidPrice1, 
                                                             ask=tick.askPrice1))
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """分钟线更新"""
        vtSymbol = bar.vtSymbol
        
        self.insertData(MINUTE_DB_NAME, vtSymbol, bar)

        bm = self.bmDict.get(vtSymbol, None)
        if bm:
            bm.updateBar(bar)
        
        if vtSymbol in self.activeSymbolDict:
            activeSymbol = self.activeSymbolDict[vtSymbol]
            self.insertData(MINUTE_DB_NAME, activeSymbol, bar)                    
        
        self.writeDrLog(text.BAR_LOGGING_MESSAGE.format(symbol=bar.vtSymbol, 
                                                        time=bar.time, 
                                                        open=bar.open, 
                                                        high=bar.high, 
                                                        low=bar.low, 
                                                        close=bar.close))

        # ----------------------------------------------------------------------

    def onXBar(self, xmin, bar):
            """X分钟线更新"""
            vtSymbol = bar.vtSymbol

            self.insertData(MINUTE_TO_DB_NAME[xmin], vtSymbol, bar)

            if vtSymbol in self.activeSymbolDict:
                activeSymbol = self.activeSymbolDict[vtSymbol]
                self.insertData(MINUTE_TO_DB_NAME[xmin], activeSymbol, bar)

            self.writeDrLog(text.BAR_LOGGING_MESSAGE.format(symbol=bar.vtSymbol,
                                                            time=bar.time,
                                                            open=bar.open,
                                                            high=bar.high,
                                                            low=bar.low,
                                                            close=bar.close))


    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.procecssTickEvent)
        self.eventEngine.register(EVENT_RECORDER_DAY, self.handleRecorderDay)
        self.eventEngine.register(EVENT_ALLCONTRACTS, self.processContractsEvent)


    #--------------------------------------------------------------------------
    def processContractsEvent(self, event):
        contract_data = event.dict_['data']
        nl = []

        # 交易的合约代码也应可以用配置文件配置
        tradingContractData = []
        # 打开设置文件
        with open(getJsonPath(self.settingFileName, __file__)) as f:
            drsettings = json.load(f)
            if 'active' in drsettings:
                actives = drsettings['active']
                if actives != {}:
                    for i in actives:
                        tradingContractData.append(i[:-4])
                for ocn in contract_data:
                    contract = ocn.decode()
                    if contract[:1] in tradingContractData or contract[:2] in tradingContractData:
                        nl.append([contract, "CTP"])

                from operator import itemgetter, attrgetter
                filename = 'openInterest.json'
                # 打开持仓量文件
                with open(getJsonPath(filename, __file__)) as f:
                    openinterests = json.load(f)
                    if 'oi' in openinterests:
                        ois = openinterests['oi']
                        for item in tradingContractData:
                            oiarray = []
                            # 获取持仓量列表
                            for oi in ois:
                                if oi[:1] == item or oi[:2] == item:
                                    oiarray.append([oi, ois[oi]])
                            # 排序持仓量列表
                            if oiarray != []:
                                sortedioarray = sorted(oiarray, key=itemgetter(1), reverse=True)
                                if sortedioarray[0][1] / sortedioarray[1][1] > 1.1 and sortedioarray[0][0] > sortedioarray[1][0]:
                                    if actives[item + '.HOT'] != sortedioarray[0][0]:
                                        actives[item + '.HOT'] = sortedioarray[0][0]
        json_data = {'working': True, 'tick': {}, 'bar': nl, 'active': actives}
        d1 = json.dumps(json_data, sort_keys=True, indent=4)

        f = open(os.path.join(os.getcwd(), self.settingFileName), 'w')
        f.write(d1)
        f.close()
        self.loadSetting()

    # #------------------------------------------------------------------------
    # def saveContractMain(self):
    #
    #     from operator import itemgetter, attrgetter
    #     filename = 'openInterest.json'
    #     activefilename = 'active.json'
    #     # 交易的合约代码也应可以用配置文件配置
    #     tradingContractData = []
    #     # 打开设置文件
    #     with open(getJsonPath(activefilename, __file__)) as f:
    #         activejson = json.load(f)
    #         if 'active' in activejson:
    #             actives = activejson['active']
    #             if actives != {}:
    #                 for i in actives:
    #                     tradingContractData.append(i)
    #         activejson['active'] = {}
    #     # 打开持仓量文件
    #     with open(getJsonPath(filename, __file__)) as f:
    #         openinterests = json.load(f)
    #         if 'oi' in openinterests:
    #             ois = openinterests['oi']
    #             for item in tradingContractData:
    #                 oiarray = []
    #                 # 获取持仓量列表
    #                 for oi in ois:
    #                     if oi[:1] == item or oi[:2] == item:
    #                         oiarray.append([oi, ois[oi]])
    #                 # 排序持仓量列表
    #                 if oiarray != []:
    #                     sortedioarray = sorted(oiarray, key=itemgetter(1), reverse=True)
    #                     if sortedioarray[0][1] / sortedioarray[1][1] > 1.1:
    #                         if actives[item] != sortedioarray[0][0]:
    #                             actives[item] = sortedioarray[0][0]
    #             # 把主力合约的代码添加到设置文件中
    #             activejson['active'] = actives
    #             d1 = json.dumps(activejson, sort_keys=True, indent=4)
    #             f = open(os.path.join(os.getcwd(), activefilename), 'w')
    #             f.write(d1)
    #             f.close()




    #--------------------------------------------------------------------------
    ##处理日线数据
    def handleRecorderDay(self, event):
        """从数据库中读取Bar数据，startDate是datetime对象"""

        oi = {}
        for contact_ in self.barSymbolSet:

            time_now = datetime.now()
            if datetime.today().weekday() == 0:
                #周一接上周五的夜盘
                time_yes = time_now + timedelta(-3)
            else:
                time_yes = time_now  + timedelta(-1)
            startDate = datetime(time_yes.year, time_yes.month,time_yes.day,21) #前一天 9点

            d = {'datetime':{'$gte':startDate}}

            barData = self.mainEngine.dbQuery(MINUTE_15_DB_NAME, contact_, d, 'datetime')

            day_bar =None
            for bar in barData:
                # 尚未创建对象
                if not day_bar:
                    day_bar = VtBarData()

                    day_bar.vtSymbol = bar['vtSymbol']
                    day_bar.symbol = bar['symbol']
                    day_bar.exchange = bar['exchange']

                    day_bar.open = bar['open']
                    day_bar.high = bar['high']
                    day_bar.low = bar['low']
                # 累加老K线
                else:
                    day_bar.high = max(day_bar.high, bar['high'])
                    day_bar.low = min(day_bar.low, bar['low'])

                # 通用部分
                day_bar.close = bar['close']
                day_bar.datetime = bar['datetime']
                day_bar.openInterest = bar['openInterest']

                day_bar.volume += int(bar['volume'])

            if day_bar:
                day_bar.datetime = datetime(time_now.year, time_now.month,time_now.day)
                day_bar.date = day_bar.datetime.strftime('%Y%m%d')
                day_bar.time = day_bar.datetime.strftime('%H:%M:%S')


                self.mainEngine.dbInsert(DAILY_DB_NAME, contact_, day_bar.__dict__)

                if contact_ in self.activeSymbolDict:
                    activeSymbol = self.activeSymbolDict[contact_]
                    self.mainEngine.dbInsert(DAILY_DB_NAME, activeSymbol, day_bar.__dict__)

                # 写入持仓量数据
                oi[day_bar.symbol] = day_bar.openInterest

                    # 保存持仓量数据
        filename = 'openInterest.json'
        json_data = {'oi': oi}
        d1 = json.dumps(json_data, sort_keys=True, indent=4)
        f = open(os.path.join(os.getcwd(), filename), 'w')
        f.write(d1)
        f.close()



 
    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是VtTickData或者VtBarData）"""
        self.queue.put((dbName, collectionName, data.__dict__))
        
    #----------------------------------------------------------------------
    def run(self):
        """运行插入线程"""
        while self.active:
            try:
                dbName, collectionName, d = self.queue.get(block=True, timeout=1)
                
                # 这里采用MongoDB的update模式更新数据，在记录tick数据时会由于查询
                # 过于频繁，导致CPU占用和硬盘读写过高后系统卡死，因此不建议使用
                #flt = {'datetime': d['datetime']}
                #self.mainEngine.dbUpdate(dbName, collectionName, d, flt, True)
                
                # 使用insert模式更新数据，可能存在时间戳重复的情况，需要用户自行清洗
                try:
                    self.mainEngine.dbInsert(dbName, collectionName, d)
                except DuplicateKeyError:
                    self.writeDrLog(u'键值重复插入失败，报错信息：%s' %traceback.format_exc())
            except Empty:
                pass
            
    #----------------------------------------------------------------------
    def start(self):
        """启动"""
        self.active = True
        self.thread.start()
        
    #----------------------------------------------------------------------
    def stop(self):
        """退出"""
        if self.active:
            self.active = False
            self.thread.join()
        
    #----------------------------------------------------------------------
    def writeDrLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_DATARECORDER_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)


class RecorderBarManager(object):
        """
        K线合成器，支持：
        1. 基于Tick合成1分钟K线
        2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30、60）
        """

        # ----------------------------------------------------------------------
        def __init__(self, onBar, onMyXminBar=None, xmin=0, onXminBar=None):
            """Constructor"""
            self.bar = None  # 1分钟K线对象
            self.onBar = onBar  # 1分钟K线回调函数

            self.xminBar = None  # X分钟K线对象
            self.xmin = xmin  # X的值
            self.onXminBar = onXminBar  # X分钟K线的回调函数

            self.lastTick = None  # 上一TICK缓存对象

            self.myXminBar = {}
            self.myXminBar[3] = None;
            self.myXminBar[5] = None;
            self.myXminBar[15] = None;
            self.myXminBar[30] = None;
            self.myXminBar[60] = None;

            self.onMyXminBar = onMyXminBar;

        # ----------------------------------------------------------------------
        def updateTick(self, tick):
            """TICK更新"""
            newMinute = False  # 默认不是新的一分钟

            if tick.lastPrice == 0.0:  ##过滤当前价为0的。
                return

            # 尚未创建对象
            if not self.bar:
                    self.bar = VtBarData()
                    newMinute = True
            # 新的一分钟
            elif self.bar.datetime.minute != tick.datetime.minute and \
                    tick.datetime - self.bar.datetime <= timedelta(0, 60):
                    # 生成上一分钟K线的时间戳
                    self.bar.datetime = tick.datetime
                    self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
                    self.bar.date = self.bar.datetime.strftime('%Y%m%d')
                    self.bar.time = self.bar.datetime.strftime('%H:%M:%S')
                    if not (self.bar.datetime ==
                            datetime.strptime(' '.join([tick.date, '21:00:00']), '%Y%m%d %H:%M:%S')
                            or self.bar.datetime ==
                            datetime.strptime(' '.join([tick.date, '09:00:00']), '%Y%m%d %H:%M:%S')):
                         # 推送已经结束的上一分钟K线
                        self.onBar(self.bar)

                    # 创建新的K线对象
                    self.bar = VtBarData()
                    newMinute = True

            # 初始化新一分钟的K线数据
            if newMinute:
                self.bar.vtSymbol = tick.vtSymbol
                self.bar.symbol = tick.symbol
                self.bar.exchange = tick.exchange

                self.bar.open = tick.lastPrice
                self.bar.high = tick.lastPrice
                self.bar.low = tick.lastPrice
            # 累加更新老一分钟的K线数据
            else:
                self.bar.high = max(self.bar.high, tick.lastPrice)
                self.bar.low = min(self.bar.low, tick.lastPrice)

            # 通用更新部分
            self.bar.close = tick.lastPrice
            self.bar.datetime = tick.datetime
            self.bar.openInterest = tick.openInterest

            if self.lastTick:
                self.bar.volume += (tick.volume - self.lastTick.volume)  # 当前K线内的成交量

            # 缓存Tick
            self.lastTick = tick

        # ----------------------------------------------------------------------
        def updateBar(self, bar):
            for min in self.myXminBar:
                self.updateMyBar(min, bar)

        # ----------------------------------------------------------------------

        def updateMyBar(self, minute, bar):
            """1分钟K线更新"""
            # 尚未创建对象
            if not self.myXminBar[minute]:
                self.myXminBar[minute] = VtBarData()

                self.myXminBar[minute].vtSymbol = bar.vtSymbol
                self.myXminBar[minute].symbol = bar.symbol
                self.myXminBar[minute].exchange = bar.exchange

                self.myXminBar[minute].open = bar.open
                self.myXminBar[minute].high = bar.high
                self.myXminBar[minute].low = bar.low
            # 累加老K线
            else:
                self.myXminBar[minute].high = max(self.myXminBar[minute].high, bar.high)
                self.myXminBar[minute].low = min(self.myXminBar[minute].low, bar.low)

            # 通用部分
            self.myXminBar[minute].close = bar.close
            self.myXminBar[minute].datetime = bar.datetime
            self.myXminBar[minute].openInterest = bar.openInterest
            self.myXminBar[minute].volume += int(bar.volume)

            # X分钟已经走完
            if not bar.datetime.minute % minute:  # 可以用X整除
                # 生成上一X分钟K线的时间戳
                self.myXminBar[minute].datetime = self.myXminBar[minute].datetime.replace(second=0,
                                                                                          microsecond=0)  # 将秒和微秒设为0
                self.myXminBar[minute].date = self.myXminBar[minute].datetime.strftime('%Y%m%d')
                self.myXminBar[minute].time = self.myXminBar[minute].datetime.strftime('%H:%M:%S.%f')

                # 推送
                self.onMyXminBar(minute, self.myXminBar[minute])

                # 清空老K线缓存对象
                self.myXminBar[minute] = None