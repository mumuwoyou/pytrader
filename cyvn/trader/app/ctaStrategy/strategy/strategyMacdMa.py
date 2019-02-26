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
class MacdMaStrategy(CtaTemplate):
    """基于MacdMa的交易策略"""
    className = 'MacdMaStrategy'
    author = u'用Python的交易员'

    # 策略参数
    initDays = 20           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    trailingPercent = 0.8   # 百分比移动止损
    openBuy = False         # 开多仓
    openShort = False       # 开空仓
    stoploss = 20           # 固定止损
    stopfit = 60            # 固定止盈
    trailingloss = 30       # 移动止损
    # 策略变量

    intraTradeHigh = 0                  # 持仓期内的最高点
    intraTradeLow = 0                   # 持仓期内的最低点
    maBuy = False                       # MA买入
    maShort = False                     # MA卖出
    macdBuy = False                     # MACD买入
    macdShort = False                   # MACD卖出
    count = 0                           # 持仓周期

    fastMa = 0
    slowMa = 0
    dif = 0
    dea = 0
    macdbar = 0



    buyOrderIDList = []                 # OCO委托买入开仓的委托号
    shortOrderIDList = []               # OCO委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'openBuy',
                 'openShort'
                 ]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'fastMa',
               'slowMa',
               'dif',
               'dea',
               'Macdbar',
               'maBuy',
               'maShort',
               'macdBuy',
               'macdShort'
               ]
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow',
                'count']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MacdMaStrategy, self).__init__(ctaEngine, setting)
        
        self.bg = BarGenerator(self.onBar, 5, self.onFiveBar)     # 创建K线合成器对象
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
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
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
        fast_ma = talib.MA(am.close, 5)
        slow_ma = talib.MA(am.close, 13)

        dif, dea, macdbar = talib.MACD(am.close, fastperiod=12, slowperiod=24, signalperiod=9)

        self.fastMa = fast_ma[-1]
        self.slowMa = slow_ma[-1]
        self.dif = dif[-1]
        self.dea = dea[-1]
        self.macdbar = macdbar

        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low
            self.count = 0

        elif self.pos > 0:
            self.count += 1
            # 计算多头持有期内的最高价，以及重置最低价
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low

            # 计算多头移动止损
            longStop = self.intraTradeHigh * (1 - self.trailingPercent / 100)

            # 发出本地止损委托
            self.sell(longStop, abs(self.pos), stop=True)

        # 持有空头仓位
        elif self.pos < 0:
            self.count += 1
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.intraTradeHigh = bar.high

            shortStop = self.intraTradeLow * (1 + self.trailingPercent / 100)
            self.cover(shortStop, abs(self.pos), stop=True)



        # 判断是否要进行交易

        # 多头
        if fast_ma[-1] > slow_ma[-1] and fast_ma[-2] < slow_ma[-2]:
            self.writeCtaLog(u'%s策略均线金叉' % self.name)
            self.maBuy = True
            self.maShort = False

        # 空头

        if fast_ma[-1] < slow_ma[-1] and fast_ma[-2] > slow_ma[-2]:
            self.writeCtaLog(u'%s策略均线死叉' % self.name)
            self.maShort = True
            self.maBuy = False

        if abs(dif[-1]) < 3 or abs(dea[-1] < 3):
            self.writeCtaLog(u'%s策略MACD进入可交易区间' % self.name)

            if dif[-1] > dea[-1] and dif[-2] < dea[-2]:
                self.writeCtaLog(u'%s策略MACD金叉' % self.name)
                self.macdBuy = True
                self.macdShort = False

            if dif[-1] < dea[-1] and dif[-2] > dea[-2]:
                self.writeCtaLog(u'%s策略MACD死叉' % self.name)
                self.macdShort = True
                self.macdBuy = False

        if self.pos == 0:
            # 买入
            if self.openBuy and self.maBuy and self.macdBuy:
                orderID = self.buy(bar.close + 5, self.fixedSize)
                self.orderList.extend(orderID)
                self.sell(bar.close - self.stoploss, self.fixedSize, stop=True)
                self.sell(bar.close + self.stopfit, self.fixedSize, stop=True)
            # 卖出
            if self.openShort and self.maShort and self.maShort:
                orderID = self.short(bar.close - 5, self.fixedSize)
                self.orderList.extend(orderID)
                self.cover(bar.close + self.stoploss, self.fixedSize, stop=True)
                self.cover(bar.close - self.stopfit, self.fixedSize, stop=True)



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

                
        # 发出状态更新事件
        self.putEvent()


    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass