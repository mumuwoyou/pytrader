# encoding: UTF-8

"""
横盘突破策略
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
class HorizBreakoutStrategy(CtaTemplate):
    """基于Adxr的交易策略"""
    className = 'AdxrStrategy'
    author = u'用Python的交易员'

    # 策略参数
    trailingPrcnt = 0.8     # 移动止损
    initDays =  30          # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    aPeriod = 11          # 窗口数

    # 策略变量

    intraTradeHigh = 0                  # 持仓期内的最高点
    intraTradeLow = 0                   # 持仓期内的最低点

    buy_high = 0
    sell_low = 0
    buy_price = 0
    sell_price = 0
    targetPos = 0

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
               'buy_high',
               'sell_low',
               'buy_price',
               'sell_price'
               ]

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(HorizBreakoutStrategy, self).__init__(ctaEngine, setting)

        self.bg = BarGenerator(self.onBar, 30, self.onMyBar)     # 创建K线合成器对象
        self.am = ArrayManager(size=50)

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

        self.putEvent()

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
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
                time.sleep(3)
                orderID = self.buy(bar.close + 5, self.fixedSize)
                self.orderList.extend(orderID)


        if self.targetPos < 0:
            if self.pos == 0:
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)
            if self.pos > 0:
                orderID = self.sell(bar.close - 5, abs(self.pos))
                self.orderList.extend(orderID)
                time.sleep(3)
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)

        if self.targetPos == 0:
            if self.pos > 0:
                orderID = self.sell(bar.close - 5, abs(self.pos))
                self.orderList.extend(orderID)
            if self.pos < 0:
                orderID = self.cover(bar.close + 5, abs(self.pos))
                self.orderList.extend(orderID)


    #----------------------------------------------------------------------
    def onMyBar(self, bar):
        """收到30分钟K线"""

        # 保存K线数据
        am = self.am
        am.updateBar(bar)

        if not am.inited:
            return

        # 计算指标数值

        h_high = max(am.high[-self.aPeriod:-1])
        l_low = min(am.low[-self.aPeriod:-1])

        vibrate = h_high - l_low < 0.04*l_low
        # 判断是否要进行交易
        # 多头
        if vibrate and am.openArray[-1] + am.highArray[-1] + am.lowArray[-1] + am.closeArray[-1]  > 4*h_high :
            self.buy_price = am.close[-1]
            self.buy_high = am.high[-1]
            self.targetPos = self.fixedSize

        # 空头
        if vibrate and am.openArray[-1] + am.highArray[-1] + am.lowArray[-1] + am.closeArray[-1] < 4*l_low:
            self.sell_price = am.close[-1]
            self.sell_low = am.low[-1]
            self.targetPos = -self.fixedSize

        if self.pos > 0 and am.high[-1] > self.buy_high:
            self.buy_high = am.high[-1]
        if self.pos < 0 and am.low[-1] < self.sell_low:
            self.sell_low = am.low[-1]

        # 平多头
        if self.pos > 0:
            if((2*am.close[-1] < self.buy_price + self.buy_high and self.buy_high > self.buy_price + 40)):
                self.targetPos = 0
            orderID = self.sell(l_low - 5, abs(self.pos), True)
            self.shortOrderIDList.extend(orderID)
        #平空头
        if self.pos < 0:
            if ((2*am.close[-1] > self.sell_price + self.sell_low and self.sell_low < self.sell_price  - 40) ):
                self.targetPos = 0
            orderID = self.cover(h_high + 5, abs(self.pos), True)
            self.buyOrderIDList.extend(orderID)


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
        if self.pos != 0:
            # 多头开仓成交后，撤消空头委托
            if self.pos > 0:
                for shortOrderID in self.shortOrderIDList:
                    self.cancelOrder(shortOrderID)
            # 反之同样
            elif self.pos < 0:
                for buyOrderID in self.buyOrderIDList:
                    self.cancelOrder(buyOrderID)

            # 移除委托号
            for orderID in (self.buyOrderIDList + self.shortOrderIDList):
                if orderID in self.orderList:
                    self.orderList.remove(orderID)

        # 发出状态更新事件
        #self.putEvent()
        pass


    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass