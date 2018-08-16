# coding: utf-8

"""
注意事项：作者不对交易盈利做任何保证，策略代码仅供参考
"""

import numpy as np
import talib
from cyvn.trader.vtObject import VtBarData
from cyvn.trader.vtConstant import EMPTY_STRING
from cyvn.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager)
from cyvn.trader.app.ctaStrategy.ctaBase import *


########################################################################
class AvgBreakStrategy(CtaTemplate):
    """基于Adxr的交易策略"""
    className = 'AvgBreakStrategy'
    author = u'用Python的交易员'

    barDbName = DAILY_DB_NAME

    # 策略参数
    trailingPrcnt = 0.8  # 移动止损
    initDays = 200  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量
    m1 = 34
    m2 = 2.2
    # 策略变量

    intraTradeHigh = 0  # 持仓期内的最高点
    intraTradeLow = 0  # 持仓期内的最低点

    model_classifier = None

    targetPos = 0

    buyOrderIDList = []  # OCO委托买入开仓的委托号
    shortOrderIDList = []  # OCO委托卖出开仓的委托号
    orderList = []  # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'm1',
                 'm2']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'targetPos'
               ]

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(AvgBreakStrategy, self).__init__(ctaEngine, setting)

        self.bg = BarGenerator(self.onBar, 15, self.onFifteenBar)  # 创建K线合成器对象
        self.am = ArrayManager(size=100)

        self.buyOrderIDList = []
        self.shortOrderIDList = []
        self.orderList = []

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)



        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onMyBar(bar)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

        self.lastTick = tick
        if self.lastTick:
            # 开多仓
            if self.pos == 0 and self.targetPos == self.fixedSize:
                orderID = self.buy(self.lastTick.askPrice1 + 2, self.fixedSize)
                self.orderList.extend(orderID)
                self.saveSyncData()
            # 开空仓
            if self.pos == 0 and self.targetPos == -self.fixedSize:
                orderID = self.short(self.lastTick.bidPrice1 - 2, self.fixedSize)
                self.orderList.extend(orderID)
                self.saveSyncData()
            # 平空开多
            if self.pos < 0 and self.targetPos == self.fixedSize:
                orderID = self.cover(self.lastTick.askPrice1 + 2, abs(self.pos))
                self.orderList.extend(orderID)
                orderID = self.buy(self.lastTick.askPrice1 + 2, self.fixedSize)
                self.orderList.extend(orderID)
                self.saveSyncData()
            # 平多开空
            if self.pos > 0 and self.targetPos == -self.fixedSize:
                orderID = self.sell(self.lastTick.bidPrice1 - 2, abs(self.pos))
                self.orderList.extend(orderID)
                orderID = self.short(self.lastTick.bidPrice1 - 2, self.fixedSize)
                self.orderList.extend(orderID)
                self.saveSyncData()
            # 平空
            if self.pos < 0 and self.targetPos == 0:
                orderID = self.cover(self.lastTick.askPrice1 + 2, abs(self.pos))
                self.orderList.extend(orderID)
                self.saveSyncData()
            # 平多
            if self.pos > 0 and self.targetPos == 0:
                orderID = self.sell(self.lastTick.bidPrice1 - 2, abs(self.pos))
                self.orderList.extend(orderID)
                self.saveSyncData()

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)

    # ---------------------------------------------------------------------
    def onFifteenBar(self, bar):
        """收到15分钟K线"""


        # 同步数据到数据库
        self.saveSyncData()

        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onMyBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 保存K线数据
        am = self.am
        am.updateBar(bar)

        if not am.inited:
            return
        long_avg = np.sum(am.close[-self.m1:-1])/self.m1
        high_price = am.high[-100:-1]
        low_price_for_atr = am.low[-100:-1]
        close_price = am.close[-100:-1]
        close_price_for_atr = close_price
        myatr = talib.ATR(high_price, low_price_for_atr, close_price_for_atr, timeperiod=14 )[-1]
        buyprice = long_avg + 2.5*myatr
        sellprice = long_avg - 2.5*myatr
        #做多
        if am.close[-1] > buyprice :
            self.targetPos = self.fixedSize
        #做空
        if am.close[-1] < sellprice :
            self.targetPos = -self.fixedSize
        #平仓
        if self.pos > 0 and am.close[-1] < long_avg:
            self .targetPos = 0
        if self.pos < 0 and am.close[-1] > long_avg:
            self.targetPos = 0
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass

