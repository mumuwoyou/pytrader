# -*- coding: utf-8 -*-

import hashlib, os, sys, tempfile, time
from datetime import datetime, timedelta
import logging
from cyvn.ctp.futures import ApiStruct, MdApi
from cyvn.trader.vtObject import *
from cyvn.trader.gateway.CtpGateway.language import text
from cyvn.trader.vtConstant import *

# 夜盘交易时间段分隔判断
NIGHT_TRADING = datetime(1900, 1, 1, 20).time()

# 全局字典, key:symbol, value:exchange
symbolExchangeDict = {}

# 交易所类型映射
exchangeMap = {}
exchangeMap[EXCHANGE_CFFEX] = 'CFFEX'
exchangeMap[EXCHANGE_SHFE] = 'SHFE'
exchangeMap[EXCHANGE_CZCE] = 'CZCE'
exchangeMap[EXCHANGE_DCE] = 'DCE'
exchangeMap[EXCHANGE_SSE] = 'SSE'
exchangeMap[EXCHANGE_INE] = 'INE'
exchangeMap[EXCHANGE_UNKNOWN] = ''
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

class CtpMdApi(MdApi):
    def __init__(self, gateway):#, brokerID, userID, password, instrumentIDs):
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.reqID = EMPTY_INT              # 操作请求编号
      
        self.userID = EMPTY_BYTE          # 账号
        self.password = EMPTY_BYTE        # 密码
        self.brokerID = EMPTY_BYTE        # 经纪商代码
        self.address = EMPTY_BYTE         # 服务器地址

        self.connectionStatus = False       # 连接状态
        self.loginStatus = False            # 登录状态
        self.subscribedSymbols = set()      # 已订阅合约代码

        self.tradingDt = None  # 交易日datetime对象
        self.tradingDate = EMPTY_STRING  # 交易日期字符串
        self.tickTime = None  # 最新行情time对象

        #self.instrumentIDs = [b'rb1805']
        self.Create()

    def Create(self):
        dir = b''.join((b'ctp.futures', self.brokerID, self.userID))
        dir = hashlib.md5(dir).hexdigest()
        dir = os.path.join(tempfile.gettempdir(), dir, 'Md') + os.sep
        if not os.path.isdir(dir): os.makedirs(dir)
        MdApi.Create(self, os.fsencode(dir) if sys.version_info[0] >= 3 else dir)

    
    def RegisterFront(self, front):
        if isinstance(front, bytes):
            return MdApi.RegisterFront(self, front)
        for front in front:
            MdApi.RegisterFront(self, front)

  

    def OnFrontConnected(self):
        #print('OnFrontConnected: Login...')
        self.connectionStatus = True
        self.writeLog(text.DATA_SERVER_CONNECTED)
        self.login()

    def OnFrontDisconnected(self, nReason):
        """服务器断开"""
        #print('OnFrontDisconnected:', nReason)
        #self.OnFrontDisconnected()
        
        self.connectionStatus = False
        self.loginStatus = False
        self.gateway.mdConnected = False
        self.writeLog(text.DATA_SERVER_DISCONNECTED)
        #self.gateway.onMarketDisconnected(nReason)
       
        

    def OnHeartBeatWarning(self, nTimeLapse):
        """心跳报警"""
        # 因为API的心跳报警比较常被触发，且与API工作关系不大，因此选择忽略
        #print('OnHeartBeatWarning:', nTimeLapse)
        pass

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        #print('OnRspUserLogin:', pRspInfo)
        """登陆回报"""
        # 如果登录成功，推送日志信息
        if pRspInfo.ErrorID == 0:
            self.loginStatus = True
            self.gateway.mdConnected = True
            
            self.writeLog(text.DATA_SERVER_LOGIN)
            
            # 重新订阅之前订阅的合约
            for subscribeReq in self.subscribedSymbols:
                self.subscribe(subscribeReq)

            # 登录时通过本地时间来获取当前的日期
            #self.tradingDt = datetime.now()
            #self.tradingDate = self.tradingDt.strftime('%Y%m%d')
                
        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = pRspInfo.ErrorID
            err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
            self.gateway.onError(err)

        #if pRspInfo.ErrorID == 0: # Success
        #    print('GetTradingDay:', self.GetTradingDay())
        #    self.SubscribeMarketData(self.instrumentIDs)

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        """订阅合约回报"""
        if pRspInfo.ErrorID :
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = pRspInfo.ErrorID
            err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
            self.gateway.onError(err)

    def OnRspUnSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        #print('OnRspUnSubMarketData:', pRspInfo)
        pass

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        #print('OnRspError:', pRspInfo)
        """错误回报"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        pass

    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast):
        """登出回报"""
        # 如果登出成功，推送日志信息
        if pRspInfo['ErrorID'] == 0:
            self.loginStatus = False
            self.gateway.mdConnected = False

            self.writeLog(text.DATA_SERVER_LOGOUT)

        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = pRspInfo.ErrorID
            err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
            self.gateway.onError(err)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        #print('OnRtnDepthMarketData:', pDepthMarketData)
        """行情推送"""


        if not pDepthMarketData.Volume and pDepthMarketData.InstrumentID:
            #self.writeLog(u'忽略成交量为0的无效单合约tick数据:')
            #self.writeLog(pDepthMarketData)
            return

        if not self.connectionStatus:
            self.connectionStatus = True


        
        # 创建对象
        tick = VtTickData()
        tick.gatewayName = self.gatewayName
        
        tick.symbol = str(pDepthMarketData.InstrumentID.decode())
        #tick.exchange = symbolExchangeDict[tick.symbol]
        #tick.exchange = str(pDepthMarketData.ExchangeID.decode()) #exchangeMapReverse.get(pDepthMarketData.ExchangeID, u'未知')
        tick.exchange = str(exchangeMapReverse.get(pDepthMarketData.ExchangeID.decode(), u'未知'))

        tick.vtSymbol = tick.symbol #'.'.join([tick.symbol, EXCHANGE_UNKNOWN])

        tick.lastPrice = pDepthMarketData.LastPrice
        tick.volume = pDepthMarketData.Volume
        tick.openInterest = pDepthMarketData.OpenInterest
        tick.time = '.'.join([str(pDepthMarketData.UpdateTime.decode()), str(int(pDepthMarketData.UpdateMillisec/100))])
        
        # 这里由于交易所夜盘时段的交易日数据有误，所以选择本地获取
        #tick.date = pDepthMarketData.TradingDay
        #tick.date = pDepthMarketData.TradingDay.decode() #time.now().strftime('%Y%m%d')

        # 先根据交易日期，生成时间
        tick.datetime = datetime.strptime(tick.date + ' ' + tick.time, '%H:%M:%S.%f')
        # 修正时间
        if tick.datetime.hour >= 20:
            if tick.datetime.isoweekday() == 1:
                # 交易日是星期一，实际时间应该是星期五
                tick.datetime = tick.datetime - timedelta(days=3)
                tick.date = tick.datetime.strftime('%Y-%m-%d')
            else:
                # 第二天
                tick.datetime = tick.datetime - timedelta(days=1)
                tick.date = tick.datetime.strftime('%Y-%m-%d')
        elif tick.datetime.hour < 8 and tick.datetime.isoweekday() == 1:
            # 如果交易日是星期一，并且时间是早上8点前 => 星期六
            tick.datetime = tick.datetime + timedelta(days=2)
            tick.date = tick.datetime.strftime('%Y-%m-%d')

        
        tick.openPrice = pDepthMarketData.OpenPrice
        tick.highPrice = pDepthMarketData.HighestPrice
        tick.lowPrice = pDepthMarketData.LowestPrice
        tick.preClosePrice = pDepthMarketData.PreClosePrice
        
        tick.upperLimit = pDepthMarketData.UpperLimitPrice
        tick.lowerLimit = pDepthMarketData.LowerLimitPrice
        
        # CTP只有一档行情
        tick.bidPrice1 = pDepthMarketData.BidPrice1
        tick.bidVolume1 = pDepthMarketData.BidVolume1
        tick.askPrice1 = pDepthMarketData.AskPrice1
        tick.askVolume1 = pDepthMarketData.AskVolume1
        tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')

        # 大商所日期转换
        if tick.exchange is EXCHANGE_DCE:
            newTime = datetime.strptime(tick.time, '%H:%M:%S.%f').time()  # 最新tick时间戳
            print(tick.exchange)
            # 如果新tick的时间小于夜盘分隔，且上一个tick的时间大于夜盘分隔，则意味着越过了12点
            if (self.tickTime and
                    newTime < NIGHT_TRADING and
                    self.tickTime > NIGHT_TRADING):
                self.tradingDt += datetime.timedelta(1)  # 日期加1
                self.tradingDate = self.tradingDt.strftime('%Y%m%d')  # 生成新的日期字符串

            tick.date = self.tradingDate  # 使用本地维护的日期

            self.tickTime = newTime  # 更新上一个tick时间


        self.gateway.onTick(tick)

    def connect(self, userID, password, brokerID, address):
        """初始化连接"""
        self.userID = userID                # 账号
        self.password = password            # 密码
        self.brokerID = brokerID            # 经纪商代码
        self.address = address              # 服务器地址
        
        # 如果尚未建立服务器连接，则进行连接
        if not self.connectionStatus:
            # 创建C++环境中的API对象，这里传入的参数是需要用来保存.con文件的文件夹路径
            #path = getTempPath(self.gatewayName + reqQryInstrument'_')
            #self.createFtdcMdApi(path)
            
            # 注册服务器地址
            self.RegisterFront(self.address)
            
            # 初始化连接，成功会调用onFrontConnected
            self.Init()
       
        # 若已经连接但尚未登录，则进行登录
        else:
            if not self.loginStatus:
                self.login()
        
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅合约"""
        # 这里的设计是，如果尚未登录就调用了订阅方法
        # 则先保存订阅请求，登录完成后会自动订阅
        if self.loginStatus:
            symbol = str(subscribeReq.symbol).encode('utf-8')
            self.SubscribeMarketData([symbol])
        self.subscribedSymbols.add(subscribeReq)   
        
    #----------------------------------------------------------------------
    def login(self):
        """登录"""
        # 如果填入了用户名密码等，则登录
        if self.userID and self.password and self.brokerID:
            req = ApiStruct.ReqUserLogin(BrokerID=self.brokerID, UserID=self.userID, Password=self.password)
            self.reqID += 1
            self.ReqUserLogin(req, self.reqID) 
  
    def writeLog(self, content):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)

    def close(self):
        self.Release()    

if __name__ == '__main__':
    mdapi = MyMdApi(b'0000', b'00000000', b'000000', [b'00000'])
    mdapi.RegisterFront(b'tcp://000.000.000.000:0000')
    mdapi.Init()

    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
