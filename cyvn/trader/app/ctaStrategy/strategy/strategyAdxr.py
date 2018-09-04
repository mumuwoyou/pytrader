# encoding: UTF-8

"""
基于King Keltner通道的交易策略，适合用在股指上，
展示了OCO委托和5分钟K线聚合的方法。

注意事项：作者不对交易盈利做任何保证，策略代码仅供参考
"""

from __future__ import division
import numpy as np
import talib
import time

from cyvn.trader.vtObject import VtBarData
from cyvn.trader.vtConstant import EMPTY_STRING
from cyvn.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator, 
                                                     ArrayManager)


########################################################################
class AdxrStrategy(CtaTemplate):
    """基于Adxr的交易策略"""
    className = 'AdxrStrategy'
    author = u'用Python的交易员'

    # 策略参数
    trailingPrcnt = 0.8     # 移动止损
    initDays =  20           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    aPeriod = 8          # 窗口数
    targetPos = 0

    # 策略变量

    intraTradeHigh = 0                  # 持仓期内的最高点
    intraTradeLow = 0                   # 持仓期内的最低点

    fastMa = 0
    middleMa = 0
    slowMa = 0
    adxr = 0
    pdi = 0
    mdi = 0


    buyOrderIDList = []                 # OCO委托买入开仓的委托号
    shortOrderIDList = []               # OCO委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'aPeriod']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'targetPos',
               'fastMa',
               'middleMa',
               'slowMa',
               'adxr',
               'pdi',
               'mdi'
               ]
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(AdxrStrategy, self).__init__(ctaEngine, setting)
        
        self.bg = BarGenerator(self.onBar, 15, self.onFifteenBar)     # 创建K线合成器对象
        self.am = ArrayManager()
        
        self.buyOrderIDList = []
        self.shortOrderIDList = []
        self.orderList = []
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）""" 
        self.bg.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)

        for orderID in self.orderList:
            self.cancelOrder(orderID)
            self.orderList = []

        if self.targetPos > 0:
            if self.pos == 0:
                orderID = self.buy(bar.close + 5, self.fixedSize)
                self.orderList.extend(orderID)
            if self.pos < 0:
                orderID = self.cover(bar.close + 5, abs(self.pos))
                self.orderList.extend(orderID)
                time.sleep(2)
                orderID = self.buy(bar.close + 5, self.fixedSize)
                self.orderList.extend(orderID)

        if self.targetPos < 0:
            if self.pos == 0:
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)
            if self.pos > 0:
                orderID = self.sell(bar.close - 5, abs(self.pos))
                self.orderList.extend(orderID)
                time.sleep(2)
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)

        if self.targetPos == 0:
            if self.pos > 0:
                orderID = self.sell(bar.close - 5, abs(self.pos))
                self.orderList.extend(orderID)
            if self.pos < 0:
                orderID = self.cover(bar.close + 5, abs(self.pos))
                self.orderList.extend(orderID)

        self.putEvent()
    
    #----------------------------------------------------------------------
    def onFifteenBar(self, bar):
        """收到15分钟K线"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []
    
        # 保存K线数据
        am = self.am
        am.updateBar(bar)

        if not am.inited:
            return
        
        # 计算指标数值

        std0 = np.std(am.close[-self.aPeriod - 1: -1])
        std1 = np.std(am.close[-self.aPeriod:])

        if std1 == 0:
            return

        volatility = (std1 - std0)/std1

        if volatility < 0.1:
            volatility = 0.1

        period = int(self.aPeriod * (1 + volatility))

        fast_ma = talib.MA(am.close, period)
        middle_ma = talib.MA(am.close, 2*period)
        slow_ma = talib.MA(am.close, 3*period)

        adxr = talib.ADXR(am.high, am.low, am.close, self.aPeriod)
        pdi = talib.PLUS_DI(am.high, am.low, am.close, self.aPeriod)
        mdi = talib.MINUS_DI(am.high, am.low, am.close, self.aPeriod)

        self.fastMa = fast_ma[-1]
        self.middleMa = middle_ma[-1]
        self.slowMa = slow_ma[-1]
        self.adxr = adxr[-1]
        self.pdi = pdi[-1]
        self.mdi = mdi[-1]

        # 判断是否要进行交易
        # 多头
        if self.adxr > 30 and self.pdi > self.mdi and self.fastMa > self.middleMa > self.slowMa:
            if self.pos < 0:
                # 这里为了保证成交，选择超价5个整指数点下单
                orderID = self.cover(bar.close + 5, abs(self.pos))
                self.orderList.extend(orderID)
                time.sleep(2)
                orderID = self.buy(bar.close + 5, self.fixedSize)
                self.orderList.extend(orderID)
            if self.pos == 0:
                orderID = self.buy(bar.close + 5, self.fixedSize)
                self.orderList.extend(orderID)
            self.targetPos = self.fixedSize

        # 空头
        if self.adxr > 30 and self.mdi > self.pdi and self.fastMa < self.middleMa < self.slowMa:
            if self.pos > 0:
                orderID = self.sell(bar.close - 5, abs(self.pos))
                self.orderList.extend(orderID)
                time.sleep(2)
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)
            if self.pos == 0:
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)
            self.targetPos = -self.fixedSize

        # 同步数据到数据库
        self.saveSyncData()

        # 发出状态更新事件
        self.putEvent()        

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass



    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # if self.pos != 0:
        #     # 多头开仓成交后，撤消空头委托
        #     if self.pos > 0:
        #         for shortOrderID in self.shortOrderIDList:
        #             self.cancelOrder(shortOrderID)
        #     # 反之同样
        #     elif self.pos < 0:
        #         for buyOrderID in self.buyOrderIDList:
        #             self.cancelOrder(buyOrderID)
        #
        #     # 移除委托号
        #     for orderID in (self.buyOrderIDList + self.shortOrderIDList):
        #         if orderID in self.orderList:
        #             self.orderList.remove(orderID)
                
        # 发出状态更新事件
        self.putEvent()


    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass