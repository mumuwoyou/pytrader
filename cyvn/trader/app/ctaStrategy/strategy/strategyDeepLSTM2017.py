# coding: utf-8

"""
注意事项：作者不对交易盈利做任何保证，策略代码仅供参考
"""

from cyvn.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager)
from cyvn.trader.app.ctaStrategy.ctaBase import *
from cyvn.comm.TAF import get_factors
from cyvn.comm.base import *
from cyvn.comm.DeepLSTM import *


########################################################################
class DeepLSTMStrategy2017(CtaTemplate):
    """基于Adxr的交易策略"""
    className = 'DeepLSTMStrategy2017'
    author = u'用Python的交易员'

    barDbName = DAILY_DB_NAME


    # 策略参数
    trailingPrcnt = 0.8     # 移动止损
    initDays =  350          # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    # 策略变量

    intraTradeHigh = 0                  # 持仓期内的最高点
    intraTradeLow = 0                   # 持仓期内的最低点

    model_classifier = None

    flag  = 0
    targetPos = 0


    buyOrderIDList = []                 # OCO委托买入开仓的委托号
    shortOrderIDList = []               # OCO委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'flag',
               'targetPos'
               ]

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DeepLSTMStrategy2017, self).__init__(ctaEngine, setting)

        self.bg = BarGenerator(self.onBar, 30, self.onFiveBar)  # 创建K线合成器对象
        self.am = ArrayManager(size=200)

        self.buyOrderIDList = []
        self.shortOrderIDList = []
        self.orderList = []

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)



        tmp = fix_data(u'data/ag88.csv')

        # targets 1d 数据合成
        tmp_1d = High_2_Low(tmp, '1d')
        rolling = 88
        targets = tmp_1d
        targets['returns'] = targets['close'].shift(-2) / targets['close'] - 1.0
        targets['upper_boundary'] = targets.returns.rolling(rolling).mean() + 0.5 * targets.returns.rolling(
            rolling).std()
        targets['lower_boundary'] = targets.returns.rolling(rolling).mean() - 0.5 * targets.returns.rolling(
            rolling).std()
        targets.dropna(inplace=True)
        targets['labels'] = 1
        targets.loc[targets['returns'] >= targets['upper_boundary'], 'labels'] = 2
        targets.loc[targets['returns'] <= targets['lower_boundary'], 'labels'] = 0

        # factors 1d 数据合成
        tmp_1d = High_2_Low(tmp, '1d')
        Index = tmp_1d.index
        High = tmp_1d.high.values
        Low = tmp_1d.low.values
        Close = tmp_1d.close.values
        Open = tmp_1d.open.values
        Volume = tmp_1d.volume.values
        factors = get_factors(Index, Open, Close, High, Low, Volume, rolling=26, drop=True)
        factors = factors.loc[:targets.index[-1]]
        tmp_factors_1 = factors.iloc[:12]
        targets = targets.loc[tmp_factors_1.index[-1]:]
        gather_list = np.arange(factors.shape[0])[11:]
        # #### 转换数据
        inputs = np.array(factors).reshape(-1, 1, factors.shape[1])
        targets = dense_to_one_hot(targets['labels'])
        targets = np.expand_dims(targets, axis=1)

        a = Classifier_DNCoreDeepLSTM(
            inputs,
            targets,
            gather_list,
            hidden_size=50,
            memory_size=50,
            learning_rate=1e-3,
            l2_coefficient=1e-3)

        a.restore_trainable_variables('models/DNCoreDeepLSTM_NADM_saver_6.ckpt')
        self.model_classifier = a

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onMyBar(bar)

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
        self.putEvent()

    #---------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""

     # 同步数据到数据库
        self.saveSyncData()

        # 发出状态更新事件
        self.putEvent()



    #----------------------------------------------------------------------
    def onMyBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 保存K线数据
        am = self.am
        am.updateBar(bar)

        if not am.inited:
            return


        tmp_factors =get_factors(
            pd.to_datetime(am.datetimeArray),
            am.openArray,
            am.closeArray,
            am.highArray,
            am.lowArray,
            am.volumeArray,
            rolling=26,
            drop = True)
        inputs = np.expand_dims(np.array(tmp_factors), axis=1)

        # 模型预测
        probability, classification = self.model_classifier.pred(inputs)
        flag = classification[-1][0]
        self.flag = flag

        #沽空
        if flag == 0:
            self.targetPos = -self.fixedSize

        #沽多
        if flag == 2:
            self.targetPos = self.fixedSize

        #震荡
        if flag == 1:
             self.targetPos = 0

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

