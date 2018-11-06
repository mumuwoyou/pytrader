# coding: utf-8

"""
注意事项：作者不对交易盈利做任何保证，策略代码仅供参考
"""

import numpy as np
import talib
from cyvn.trader.vtObject import VtBarData
from cyvn.trader.vtConstant import EMPTY_STRING
from cyvn.trader.app.ctaStrategy.ctaTemplate import (TargetPosTemplate,
                                                     BarGenerator,
                                                     ArrayManager)
from cyvn.trader.app.ctaStrategy.ctaBase import *


########################################################################
class AvgBreakStrategy(TargetPosTemplate):
    """基于Adxr的交易策略"""
    className = 'AvgBreakStrategy'
    author = u'用Python的交易员'


    # 策略参数
    trailingPrcnt = 0.8  # 移动止损
    initDays = 30 # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量
    m1 = 34
    m2 = 2.2
    # 策略变量

    intraTradeHigh = 0  # 持仓期内的最高点
    intraTradeLow = 0  # 持仓期内的最低点

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

        self.bg = BarGenerator(self.onBar, 15, self.onMyBar)  # 创建K线合成器对象
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
            self.onBar(bar)

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
        TargetPosTemplate.onTick(self, tick)
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        TargetPosTemplate.onBar(self, bar)
        self.bg.updateBar(bar)


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
        myatr = talib.ATR(high_price, low_price_for_atr, close_price_for_atr, timeperiod=14)[-1]
        buyprice = long_avg + 2.5*myatr
        sellprice = long_avg - 2.5*myatr
        #做多
        if am.close[-1] > buyprice :
            self.setTargetPos(self.fixedSize)
        #做空
        if am.close[-1] < sellprice :
            self.setTargetPos(-self.fixedSize)
        #平仓
        if self.pos > 0 and am.close[-1] < long_avg:
            self .setTargetPos(0)
        if self.pos < 0 and am.close[-1] > long_avg:
            self.setTargetPos(0)

        # 同步数据到数据库
        self.saveSyncData()
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

