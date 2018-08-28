# -*- coding:utf-8 -*-


import os
import json
from copy import copy
from datetime import datetime
import hashlib, sys, tempfile, time
import logging
from cyvn.trader.vtGateway import *
from cyvn.trader.vtFunction import getTempPath
from cyvn.trader.gateway.CtpGateway.language.chinese import text
from cyvn.trader.vtConstant import *
from .ctpMdApi import *


from cyvn.ctp.futures import ApiStruct, TraderApi



PRICETYPE_LIMITPRICE = ApiStruct.OPT_LimitPrice
PRICETYPE_MARKETPRICE = ApiStruct.OPT_BestPrice


DIRECTION_LONG = ApiStruct.D_Buy #"THOST_FTDC_D_Buy" #买
DIRECTION_SHORT = ApiStruct.D_Sell  #"THOST_FTDC_D_Sell" #卖

OFFSET_OPEN = ApiStruct.OF_Open #"THOST_FTDC_OF_Open" #开仓
OFFSET_CLOSE = ApiStruct.OF_Close #"THOST_FTDC_OF_Close" #平仓
OFFSET_FORCE_CLOSE = ApiStruct.OF_ForceClose #"THOST_FTDC_OF_ForceClose" #强平
OFFSET_CLOSETODAY = ApiStruct.OF_CloseToday #"THOST_FTDC_OF_CloseToday" #平今
OFFSET_CLOSEYESTERDAY =  ApiStruct.OF_CloseYesterday #"THOST_FTDC_OF_CloseYesterday" #平昨


POSITION_NET = ApiStruct.PD_Net #"THOST_FTDC_PD_Net" #净
POSITION_LONG = ApiStruct.PD_Long #"THOST_FTDC_PD_Long" #多头
POSITION_SHORT =  ApiStruct.PD_Short #"THOST_FTDC_PD_Short" #空头

PRODUCT_FUTURES = ApiStruct.PC_Futures #"THOST_FTDC_PC_Futures" #期货
PRODUCT_OPTION = ApiStruct.PC_Options #"THOST_FTDC_PC_Options" #期货期权
PRODUCT_COMBINATION = ApiStruct.PC_Combination #"THOST_FTDC_PC_Combination" #组合



STATUS_ALLTRADED = ApiStruct.OST_AllTraded #"THOST_FTDC_OST_AllTraded" #全部成交
STATUS_ALLTRADED = ApiStruct.OST_PartTradedQueueing #"THOST_FTDC_OST_PartTradedQueueing" #部分成交还在队列中
STATUS_PART_TRADE_NOT_QUEUEING = ApiStruct.OST_PartTradedNotQueueing #"THOST_FTDC_OST_PartTradedNotQueueing" #部分成交不在队列中
STATUS_TRADE_QUEUEING = ApiStruct.OST_NoTradeQueueing #"THOST_FTDC_OST_NoTradeQueueing" #未成交还在队列中
STATUS_NOTRADE_NOT_QUEUEING = ApiStruct.OST_NoTradeNotQueueing #"THOST_FTDC_OST_NoTradeNotQueueing" #未成交不在队列中
STATUS_CANCELED = ApiStruct.OST_Canceled #"THOST_FTDC_OST_Canceled" #撤单
STATUS_UNKNOW = ApiStruct.OST_Unknown #"THOST_FTDC_OST_Unknown" #未知
STATUS_NOT_TOUCHED = ApiStruct.OST_NotTouched #"THOST_FTDC_OST_NotTouched" #尚未触发
STATUS_TOUCHED = ApiStruct.OST_Touched #"THOST_FTDC_OST_Touched" #已触发

"""
#----------------------------------------------
# 以下为一些VT类型和CTP类型的映射字典
# 价格类型映射
priceTypeMap = {}
priceTypeMap[PRICETYPE_LIMITPRICE] = defineDict["THOST_FTDC_OPT_LimitPrice"]
priceTypeMap[PRICETYPE_MARKETPRICE] = defineDict["THOST_FTDC_OPT_AnyPrice"]
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()} 

# 方向类型映射
directionMap = {}
directionMap[DIRECTION_LONG] = defineDict['THOST_FTDC_D_Buy']
directionMap[DIRECTION_SHORT] = defineDict['THOST_FTDC_D_Sell']
directionMapReverse = {v: k for k, v in directionMap.items()}

# 开平类型映射
offsetMap = {}
offsetMap[OFFSET_OPEN] = defineDict['THOST_FTDC_OF_Open']
offsetMap[OFFSET_CLOSE] = defineDict['THOST_FTDC_OF_Close']
offsetMap[OFFSET_CLOSETODAY] = defineDict['THOST_FTDC_OF_CloseToday']
offsetMap[OFFSET_CLOSEYESTERDAY] = defineDict['THOST_FTDC_OF_CloseYesterday']
offsetMapReverse = {v:k for k,v in offsetMap.items()}

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

# 持仓类型映射
posiDirectionMap = {}
posiDirectionMap[DIRECTION_NET] = defineDict["THOST_FTDC_PD_Net"]
posiDirectionMap[DIRECTION_LONG] = defineDict["THOST_FTDC_PD_Long"]
posiDirectionMap[DIRECTION_SHORT] = defineDict["THOST_FTDC_PD_Short"]
posiDirectionMapReverse = {v:k for k,v in posiDirectionMap.items()}

# 产品类型映射
productClassMap = {}
productClassMap[PRODUCT_FUTURES] = defineDict["THOST_FTDC_PC_Futures"]
productClassMap[PRODUCT_OPTION] = defineDict["THOST_FTDC_PC_Options"]
productClassMap[PRODUCT_COMBINATION] = defineDict["THOST_FTDC_PC_Combination"]
productClassMapReverse = {v:k for k,v in productClassMap.items()}

# 委托状态映射
statusMap = {}
statusMap[STATUS_ALLTRADED] = defineDict["THOST_FTDC_OST_AllTraded"]
statusMap[STATUS_PARTTRADED] = defineDict["THOST_FTDC_OST_PartTradedQueueing"]
statusMap[STATUS_NOTTRADED] = defineDict["THOST_FTDC_OST_NoTradeQueueing"]
statusMap[STATUS_CANCELLED] = defineDict["THOST_FTDC_OST_Canceled"]
statusMapReverse = {v:k for k,v in statusMap.items()}
"""
priceTypeMap = {u'市价': '1', u'限价': '2'}
priceTypeMapReverse = {'1': u'市价', '2': u'限价'}
directionMap = {u'多': '0', u'空': '1'}
directionMapReverse = {'1': u'空', '0': u'多'}
offsetMap = {u'开仓': '0', u'平昨': '4', u'平仓': '1', u'平今': '3'}
offsetMapReverse = {'1': u'平仓', '0': u'开仓', '4': u'平昨', '3': u'平今'}
exchangeMap = {'DCE': 'DCE', 'INE': 'INE', 'CZCE': 'CZCE', 'CFFEX': 'CFFEX', 'SSE': 'SSE', 'UNKNOWN': '', 'SHFE': 'SHFE'}
exchangeMapReverse = {'': 'UNKNOWN', 'DCE': 'DCE', 'CZCE': 'CZCE', 'CFFEX': 'CFFEX', 'SSE': 'SSE', 'SHFE': 'SHFE', 'INE': 'INE'}
posiDirectionMap = {u'多': '2', u'净': '1', u'空': '3'}
posiDirectionMapReverse = {'1': u'净', '3': u'空', '2': u'多'}
DirectionMap = {u'多': '0', u'空': '1'}
DirectionMapReverse = {'1': u'空', '0': u'多'}
productClassMap = {u'期货': '1', u'期权': '2', u'组合': '3'}
productClassMapReverse = {'1': u'期货', '3': u'组合', '2': u'期权'}
statusMap = {u'未成交': '3', u'部分成交': '1', u'全部成交': '0', u'已撤销': '5'}
statusMapReverse = {'1': u'部分成交', '3': u'未成交', '0': u'全部成交', '5': u'已撤销'}


class CtpTdApi(TraderApi):
    """CTP交易API实现"""
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """API对象的初始化函数"""
        super(CtpTdApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.reqID = EMPTY_INT              # 操作请求编号
        self.orderRef = EMPTY_INT           # 订单编号
        
        self.connectionStatus = False       # 连接状态
        self.loginStatus = False            # 登录状态
        self.authStatus = False
        
        self.userID = EMPTY_BYTE         # 账号
        self.password = EMPTY_BYTE        # 密码
        self.brokerID = EMPTY_BYTE        # 经纪商代码
        self.address = EMPTY_BYTE         # 服务器地址
        
        self.frontID = EMPTY_INT            # 前置机编号
        self.sessionID = EMPTY_INT          # 会话编号
        
        self.posDict = {}
        self.symbolExchangeDict = {}        # 保存合约代码和交易所的印射关系
        self.symbolSizeDict = {}            # 保存合约代码和合约大小的印射关系

        self.requireAuthentication = False

        self.Create()

    def Create(self):
        dir = b''.join((b'ctp.futures', self.brokerID, self.userID))
        dir = hashlib.md5(dir).hexdigest()
        dir = os.path.join(tempfile.gettempdir(), dir, 'Trader') + os.sep
        if not os.path.isdir(dir): os.makedirs(dir)
        TraderApi.Create(self, os.fsencode(dir) if sys.version_info[0] >= 3 else dir)    

    def RegisterFront(self, front):
        if isinstance(front, bytes):
            return TraderApi.RegisterFront(self, front)
        for front in front:
            TraderApi.RegisterFront(self, front)
    #----------------------------------------------------------------------
    def OnFrontConnected(self):
        """服务器连接"""
        self.connectionStatus = True
    
        self.writeLog(text.TRADING_SERVER_CONNECTED)
        
        if self.requireAuthentication:
            self.authenticate()
        else:
            self.login()
        
    #----------------------------------------------------------------------
    def OnFrontDisconnected(self, nReason):
        """服务器断开"""
        self.connectionStatus = False
        self.loginStatus = False
        self.gateway.tdConnected = False
    
        self.writeLog(text.TRADING_SERVER_DISCONNECTED)
        
    #----------------------------------------------------------------------
    def OnHeartBeatWarning(self, nTimeLapse):
        """"""
        pass
        
    #----------------------------------------------------------------------
    def OnRspAuthenticate(self, pRspAuthenticate, pRspInfo, nRequestID, bIsLast):
        """验证客户端回报"""
        if pRspInfo.ErrorID == 0:
            self.authStatus = True
            
            self.writeLog(text.TRADING_SERVER_AUTHENTICATED)
            
            self.login()
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = pRspInfo.ErrorID
            err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
            self.gateway.onError(err)
        
    #----------------------------------------------------------------------
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        """登陆回报"""
        # 如果登录成功，推送日志信息
        if pRspInfo.ErrorID == 0:
            self.frontID = str(pRspUserLogin.FrontID)
            self.sessionID = str(pRspUserLogin.SessionID)
            self.loginStatus = True
            self.gateway.tdConnected = True
            
            self.writeLog(text.TRADING_SERVER_LOGIN)
            
            # 确认结算信息
            req = ApiStruct.QrySettlementInfoConfirm(BrokerID = self.brokerID, InvestorID = self.userID)
            self.reqID += 1
            self.ReqSettlementInfoConfirm(req, self.reqID)              
                
        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = pRspInfo.ErrorID
            err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
            self.gateway.onError(err)
        
    #----------------------------------------------------------------------
    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast):
   
        """登出回报"""
        # 如果登出成功，推送日志信息
        if pRspInfo.ErrorID == 0:
            self.loginStatus = False
            self.gateway.tdConnected = False
            
            self.writeLog(text.TRADING_SERVER_LOGOUT)
                
        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = pRspInfo.ErrorID
            err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
            self.gateway.onError(err)
        
 
        
    #----------------------------------------------------------------------
    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast):
        """发单错误（柜台）"""
        # 推送委托信息
        #print(pInputOrder)
        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.symbol = pInputOrder.InstrumentID.decode()
        order.exchange = exchangeMapReverse.get(pInputOrder.ExchangeID.decode(), '')
        order.vtSymbol = order.symbol.decode()
        order.orderID = pInputOrder.OrderRef
        order.vtOrderID = '.'.join([self.gatewayName, order.orderID])
        order.direction = directionMapReverse.get(pInputOrder.Direction, DIRECTION_UNKNOWN)
        order.offset = offsetMapReverse.get(pInputOrder.CombOffsetFlag, OFFSET_UNKNOWN)
        order.status = STATUS_REJECTED
        order.price = pInputOrder.LimitPrice
        order.totalVolume = pInputOrder.VolumeTotalOriginal
        self.gateway.onOrder(order)
        
        # 推送错误信息
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        
   
        
    #----------------------------------------------------------------------
    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast):
        
        """撤单错误（柜台）"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        
  
        
    #----------------------------------------------------------------------
    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):

        """确认结算信息回报"""
        self.writeLog(text.SETTLEMENT_INFO_CONFIRMED)
        
        # 查询合约代码
        self.reqID += 1
        req = ApiStruct.QryInstrument()
        self.ReqQryInstrument(req, self.reqID)

          
    #----------------------------------------------------------------------
    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        """持仓查询回报"""
        #print("OnRspQryInvestorPosition:", pInvestorPosition)
        if not pInvestorPosition:
            return
        
        # 获取持仓缓存对象
        posName = '.'.join([str(pInvestorPosition.InstrumentID.decode()), str(pInvestorPosition.PosiDirection.decode())])
        if posName in self.posDict:
            pos = self.posDict[posName]
        else:
            pos = VtPositionData()
            self.posDict[posName] = pos

            pos.gatewayName = self.gatewayName
            pos.symbol = pInvestorPosition.InstrumentID.decode()
            pos.vtSymbol = pos.symbol
            pos.direction = posiDirectionMapReverse.get(str(pInvestorPosition.PosiDirection.decode()), '')
            pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction]) 
        
        # 针对上期所持仓的今昨分条返回（有昨仓、无今仓），读取昨仓数据
        if pInvestorPosition.YdPosition and not pInvestorPosition.TodayPosition:
            pos.ydPosition = pInvestorPosition.Position
            
        # 计算成本
        #size = self.symbolSizeDict[pos.symbol]
        cost = pos.price * pos.position #* size
        
        # 汇总总仓
        pos.position += pInvestorPosition.Position
        pos.positionProfit += pInvestorPosition.PositionProfit
        
        # 计算持仓均价
        if pos.position and pos.symbol in self.symbolSizeDict:
            size = self.symbolSizeDict[pos.symbol]
            if size > 0 and pos.position >0:
                pos.price = (cost + pInvestorPosition.PositionCost) / abs(pos.position * size)
        
        # 读取冻结
        if pos.direction is DIRECTION_LONG: 
            pos.frozen += pInvestorPosition.LongFrozen
        else:
            pos.frozen += pInvestorPosition.ShortFrozen
        
        # 查询回报结束
        if bIsLast:
            # 遍历推送
            for pos in self.posDict.values():
                self.gateway.onPosition(pos)
            
            # 清空缓存
            self.posDict.clear()

    #----------------------------------------------------------------------
    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        """持仓明细查询回报"""
        #print(pInvestorPositionDetail)
        if not pInvestorPositionDetail:
            return
        posBuffer = PositionDetailBuffer(pInvestorPositionDetail, self.gatewayName)
        pos = posBuffer.updateBuffer(pInvestorPositionDetail)
        if pos.symbol:
            self.gateway.onPositionDetail(pos)
        #print(pos.vtPositionDetailName, pos.tradeid, pos.position, pos.opendate, pos.openprice, pos.exchange, pos.gatewayName)
        
    #----------------------------------------------------------------------
    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        """资金账户查询回报"""
        account = VtAccountData()
        account.gatewayName = self.gatewayName
    
        # 账户代码
        account.accountID = pTradingAccount.AccountID.decode()
        account.vtAccountID = '.'.join([self.gatewayName, account.accountID])
    
        # 数值相关
        account.preBalance = pTradingAccount.PreBalance
        account.available = pTradingAccount.Available
        account.commission = pTradingAccount.Commission
        account.margin = pTradingAccount.CurrMargin
        account.closeProfit = pTradingAccount.CloseProfit
        account.positionProfit = pTradingAccount.PositionProfit
    
        # 这里的balance和快期中的账户不确定是否一样，需要测试
        account.balance = (pTradingAccount.PreBalance - pTradingAccount.PreCredit - pTradingAccount.PreMortgage +
                           pTradingAccount.Mortgage - pTradingAccount.Withdraw + pTradingAccount.Deposit +
                           pTradingAccount.CloseProfit + pTradingAccount.PositionProfit + pTradingAccount.CashIn -
                           pTradingAccount.Commission)
    
        # 推送
        self.gateway.onAccount(account)
        
   
        
    #----------------------------------------------------------------------
    def OnRspQryInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast):
        """合约查询回报"""
        #print("rssp instrument:", pInstrument.ExchangeID)
        contract = VtContractData()
        contract.gatewayName = self.gatewayName

        contract.symbol = str(pInstrument.InstrumentID.decode())
        contract.exchange = str(pInstrument.ExchangeID.decode()) # exchangeMapReverse[pInstrument.ExchangeID]
        contract.vtSymbol = contract.symbol#'.'.join([contract.symbol, contract.exchange])
        contract.name = pInstrument.InstrumentName.decode('GBK')
        #print(type(pInstrument.InstrumentID), type(pInstrument.ExchangeID), pInstrument.InstrumentID)
        #print(contract.symbol)
        # 合约数值
        contract.size = pInstrument.VolumeMultiple
        contract.priceTick = pInstrument.PriceTick
        contract.strikePrice = pInstrument.StrikePrice
        contract.underlyingSymbol = pInstrument.UnderlyingInstrID.decode()

        contract.productClass = pInstrument.ProductClass.decode() #productClassMapReverse.get(pInstrument.ProductClass, PRODUCT_UNKNOWN)

        # 期权类型
        #if pInstrument.OptionsType == '1':
        #    contract.optionType = OPTION_CALL
        #elif pInstrument.OptionsType == '2':
        #    contract.optionType = OPTION_PUT

        # 缓存代码和交易所的印射关系
        self.symbolExchangeDict[contract.symbol] = contract.exchange
        self.symbolSizeDict[contract.symbol] = contract.size

        # 推送
        self.gateway.onContract(contract)

        # 缓存合约代码和交易所映射
        symbolExchangeDict[contract.symbol] = contract.exchange

        if bIsLast:
            self.writeLog(text.CONTRACT_DATA_RECEIVED)
        
    #----------------------------------------------------------------------
    
        
    #----------------------------------------------------------------------
    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        """错误回报"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        
    #---------------------------------------   -------------------------------
    def OnRtnOrder(self, pOrder):
        """报单回报"""
        #print("OnRtnOrder:", pOrder,"\n")
        # 更新最大报单编号
        newref = pOrder.OrderRef
        self.orderRef = max(self.orderRef, int(newref))
        
        # 创建报单数据对象
        order = VtOrderData()
        order.gatewayName = self.gatewayName
        
        # 保存代码和报单号
        order.symbol = pOrder.InstrumentID.decode()
        order.exchange = exchangeMapReverse.get(str(pOrder.ExchangeID.decode()), '')
        order.vtSymbol = order.symbol #'.'.join([order.symbol, order.exchange])
        
        order.orderID = pOrder.OrderRef.decode()
        # CTP的报单号一致性维护需要基于frontID, sessionID, orderID三个字段
        # 但在本接口设计中，已经考虑了CTP的OrderRef的自增性，避免重复
        # 唯一可能出现OrderRef重复的情况是多处登录并在非常接近的时间内（几乎同时发单）
        # 考虑到VtTrader的应用场景，认为以上情况不会构成问题
        order.vtOrderID = '.'.join([self.gatewayName, order.orderID])        
        
        order.direction = directionMapReverse.get(pOrder.Direction.decode(), DIRECTION_UNKNOWN)
        order.offset = offsetMapReverse.get(pOrder.CombOffsetFlag.decode(), OFFSET_UNKNOWN)
        order.status = statusMapReverse.get(pOrder.OrderStatus.decode(), STATUS_UNKNOWN)            
            
        # 价格、报单量等数值
        order.price = pOrder.LimitPrice
        order.totalVolume = pOrder.VolumeTotalOriginal
        order.tradedVolume = pOrder.VolumeTraded
        order.orderTime = pOrder.InsertTime.decode()
        order.cancelTime = pOrder.CancelTime.decode()
        order.frontID = pOrder.FrontID
        order.sessionID = pOrder.SessionID
        
        # 推送
        self.gateway.onOrder(order)
        
    #----------------------------------------------------------------------
    def OnRtnTrade(self, pTrade):
        """成交回报"""
        # 创建报单数据对象
        #print(pTrade)
        trade = VtTradeData()
        trade.gatewayName = self.gatewayName
        
        # 保存代码和报单号
        trade.symbol = pTrade.InstrumentID.decode()
        trade.exchange = exchangeMapReverse.get(pTrade.ExchangeID.decode(), '')
        trade.vtSymbol = trade.symbol #'.'.join([trade.symbol, trade.exchange])
        
        trade.tradeID = pTrade.TradeID.decode()
        trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
        
        trade.orderID = pTrade.OrderRef.decode()
        trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])
        
        # 方向
        trade.direction = directionMapReverse.get(pTrade.Direction.decode(), '')
            
        # 开平
        trade.offset = offsetMapReverse.get(pTrade.OffsetFlag, '')
            
        # 价格、报单量等数值
        trade.price = pTrade.Price
        trade.volume = pTrade.Volume
        trade.tradeTime = pTrade.TradeTime.decode()
        
        #print("trade:",trade)
        # 推送
        self.gateway.onTrade(trade)
        
    #----------------------------------------------------------------------
    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast):
        """发单错误回报（交易所）"""
        print("OnRspOrderAction:", pInputOrderAction, "\n")

        # 推送错误信息
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        
    #----------------------------------------------------------------------
    def OnErrRtnOrderAction(self, pOrderAction, pRspInfo):
        """撤单错误回报（交易所）"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        
    #----------------------------------------------------------------------
    def onErrRtnOrderInsert(self, pOrderInsert, pRspInfo):
        """发单错误回报（交易所）"""
        # 推送委托信息
        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.symbol = pOrderInsert.InstrumentID.decode()
        order.exchange = exchangeMapReverse.get(str(pOrderInsert.ExchangeID.decode()), '')
        order.vtSymbol = order.symbol
        order.orderID = pOrderInsert.OrderRef.decode()
        order.vtOrderID = '.'.join([self.gatewayName, order.orderID])
        order.direction = directionMapReverse.get(pOrderInsert.Direction.decode(), DIRECTION_UNKNOWN)
        order.offset = offsetMapReverse.get(pOrderInsert.CombOffsetFlag.decode(), OFFSET_UNKNOWN)
        order.status = STATUS_REJECTED
        order.price = pOrderInsert.LimitPrice
        order.totalVolume = pOrderInsert.VolumeTotalOriginal
        self.gateway.onOrder(order)

        # 推送错误信息
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = pRspInfo.ErrorID
        err.errorMsg = pRspInfo.ErrorMsg.decode('gbk')
        self.gateway.onError(err)

    #----------------------------------------------------------------------
    def connect(self, userID, password, brokerID, address, authCode, userProductInfo):
        """初始化连接"""
        self.userID = userID                # 账号
        self.password = password            # 密码
        self.brokerID = brokerID            # 经纪商代码
        self.address = address              # 服务器地址
        self.authCode = authCode            #验证码
        self.userProductInfo = userProductInfo  #产品信息
        
        # 如果尚未建立服务器连接，则进行连接
        if not self.connectionStatus:
            # 创建C++环境中的API对象，这里传入的参数是需要用来保存.con文件的文件夹路径
            #path = getTempPath(self.gatewayName + '_')
            #self.createFtdcTraderApi(path)
            
            # 设置数据同步模式为推送从今日开始所有数据
            self.SubscribePrivateTopic(0)
            self.SubscribePublicTopic(0)            
            
            # 注册服务器地址
            self.RegisterFront(self.address)
            
            # 初始化连接，成功会调用onFrontConnected
            self.Init()
            
        # 若已经连接但尚未登录，则进行登录
        else:
            if self.requireAuthentication and not self.authStatus:
                self.authenticate()
            elif not self.loginStatus:
                self.login()
    
    #----------------------------------------------------------------------
    def login(self):
        """连接服务器"""
        # 如果填入了用户名密码等，则登录
        if self.userID and self.password and self.brokerID:
            req = ApiStruct.ReqUserLogin(BrokerID=self.brokerID, UserID=self.userID, Password=self.password)
            self.reqID += 1
            self.ReqUserLogin(req, self.reqID) 
            
            
    #----------------------------------------------------------------------
    def authenticate(self):
        """申请验证"""
        if self.userID and self.brokerID and self.authCode and self.userProductInfo:
            ApiStruct.ReqAuthenticate(UserID = self.userID, BrokerID = self.brokerID,
                 AuthCode = self.authCode, UserProductInfo = self.userProductInfo)
            self.reqID +=1
            self.ReqAuthenticate(req, self.reqID)

    #----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户"""
        self.reqID += 1
        req = ApiStruct.QryTradingAccount()
        self.ReqQryTradingAccount(req, self.reqID)
        
    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.reqID += 1
        req = ApiStruct.QryInvestorPosition()
        req.BrokerID = self.brokerID
        req.InvestorID = self.userID
        self.ReqQryInvestorPosition(req, self.reqID)

    # ----------------------------------------------------------------------
    def qryPositionDetail(self):
        """查询持仓明细"""
        self.reqID += 1
        req = {}
        req = ApiStruct.QryInvestorPositionDetail()
        req.BrokerID = self.brokerID
        req.InvestorID = self.userID
        self.ReqQryInvestorPositionDetail(req, self.reqID)

    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        self.reqID += 1
        self.orderRef += 1
        
        #print("send order:", type(orderReq.symbol))
        req = ApiStruct.InputOrder()
        req.InstrumentID = orderReq.symbol.encode('utf-8')
        req.LimitPrice = orderReq.price
        req.VolumeTotalOriginal = orderReq.volume
        
        # 下面如果由于传入的类型本接口不支持，则会返回空字符串
        req.OrderPriceType = priceTypeMap.get(orderReq.priceType, '').encode('utf-8')
        req.Direction = directionMap.get(orderReq.direction, '').encode('utf-8')
        req.CombOffsetFlag = offsetMap.get(orderReq.offset, '').encode('utf-8')
            
        req.OrderRef = str(self.orderRef).encode('utf-8')
        req.InvestorID = self.userID
        req.UserID = self.userID
        req.BrokerID = self.brokerID
        
        req.CombHedgeFlag = ApiStruct.HF_Speculation #defineDict['THOST_FTDC_HF_Speculation'] ,      # 投机单
        req.ContingentCondition = ApiStruct.CC_Immediately #defineDict['THOST_FTDC_CC_Immediately'], # 立即发单
        req.ForceCloseReason = ApiStruct.FCC_NotForceClose #defineDict['THOST_FTDC_FCC_NotForceClose'], # 非强平
        req.IsAutoSuspend = 0                                             # 非自动挂起
        req.TimeCondition = ApiStruct.TC_GFD # defineDict['THOST_FTDC_TC_GFD'],               # 今日有效
        req.VolumeCondition = ApiStruct.VC_AV # defineDict['THOST_FTDC_VC_AV'] ,             # 任意成交量
        req.MinVolume = 1                                                 # 最小成交量为1
        
        # 判断FAK和FOK
        if orderReq.priceType == PRICETYPE_FAK:
            req.OrderPriceType = ApiStruct.OPT_LimitPrice # defineDict["THOST_FTDC_OPT_LimitPrice"]
            req.TimeCondition = ApiStruct.THOST_FTDC_TC_IOC # defineDict['THOST_FTDC_TC_IOC']
            req.VolumeCondition = ApiStruct.VC_AV # defineDict['THOST_FTDC_VC_AV']
        if orderReq.priceType == PRICETYPE_FOK:
            req.OrderPriceType = ApiStruct.OPT_LimitPrice #defineDict["THOST_FTDC_OPT_LimitPrice"]
            req.TimeCondition = ApiStruct.THOST_FTDC_TC_IOC #defineDict['THOST_FTDC_TC_IOC']
            req.VolumeCondition = ApiStruct.VC_CV # defineDict['THOST_FTDC_VC_CV']        
        
        self.ReqOrderInsert(req, self.reqID)
        
        # 返回订单号（字符串），便于某些算法进行动态管理
        vtOrderID = '.'.join([self.gatewayName, str(self.orderRef)])
        return vtOrderID
    
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        self.reqID += 1

        req = ApiStruct.InputOrderAction()
        req.InstrumentID = cancelOrderReq.symbol.encode('utf-8')
        req.ExchangeID = cancelOrderReq.exchange.encode('utf-8')
        req.OrderRef = cancelOrderReq.orderID.encode('utf-8')
        req.FrontID = cancelOrderReq.frontID
        req.SessionID = cancelOrderReq.sessionID
        
        req.ActionFlag = ApiStruct.AF_Delete#defineDict['THOST_FTDC_AF_Delete'],
        req.BrokerID = self.brokerID
        req.InvestorID = self.userID
        
        self.ReqOrderAction(req, self.reqID)
        
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        self.Release()

    #----------------------------------------------------------------------
    def writeLog(self, content):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log) 



class PositionDetailBuffer(object):
    """用来缓存持仓明细的数据，处理上期所的数据返回分今昨的问题"""

    #----------------------------------------------------------------------
    def __init__(self, data, gatewayName):
        """Constructor"""
        self.symbol = data.InstrumentID.decode()
        self.direction = DirectionMapReverse.get(data.Direction.decode(), '')

        self.position = EMPTY_INT
        self.openprice = EMPTY_FLOAT
        self.opendate = EMPTY_STRING
        self.tradeid = EMPTY_STRING
        self.exchangeid = EMPTY_STRING

        # 通过提前创建持仓数据对象并重复使用的方式来降低开销
        pos = VtPositionDetailData()
        pos.symbol = self.symbol
        pos.vtSymbol = self.symbol
        pos.gatewayName = gatewayName
        pos.direction = self.direction
        pos.tradeid = self.tradeid
        pos.exchange = self.exchangeid
        pos.vtPositionDetailName = '.'.join([pos.vtSymbol, pos.direction])
        self.pos = pos


    def updateBuffer(self, data):

            self.pos.position = data.Volume
            self.pos.openprice = data.OpenPrice
            self.pos.opendate = data.OpenDate.decode()
            self.pos.tradeid = data.TradeID.decode('GBK')
            self.pos.exchange = data.ExchangeID.decode('GBK')

            return copy(self.pos)

"""
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
    def OnRspUnSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
    def OnRspSubForQuoteRsp(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
    def OnRspUnSubForQuoteRsp(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
    def OnRspAuthenticate(self, pRspAuthenticate, pRspInfo, nRequestID, bIsLast):
    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast):
    def OnRspUserPasswordUpdate(self, pUserPasswordUpdate, pRspInfo, nRequestID, bIsLast):
    def OnRspTradingAccountPasswordUpdate(self, pTradingAccountPasswordUpdate, pRspInfo, nRequestID, bIsLast):
  
    def OnRspParkedOrderInsert(self, pParkedOrder, pRspInfo, nRequestID, bIsLast):
    def OnRspParkedOrderAction(self, pParkedOrderAction, pRspInfo, nRequestID, bIsLast):
   
    def OnRspQueryMaxOrderVolume(self, pQueryMaxOrderVolume, pRspInfo, nRequestID, bIsLast):
   
    def OnRspRemoveParkedOrder(self, pRemoveParkedOrder, pRspInfo, nRequestID, bIsLast):
    def OnRspRemoveParkedOrderAction(self, pRemoveParkedOrderAction, pRspInfo, nRequestID, bIsLast):
    def OnRspExecOrderInsert(self, pInputExecOrder, pRspInfo, nRequestID, bIsLast):
    def OnRspExecOrderAction(self, pInputExecOrderAction, pRspInfo, nRequestID, bIsLast):
    def OnRspForQuoteInsert(self, pInputForQuote, pRspInfo, nRequestID, bIsLast):
    def OnRspQuoteInsert(self, pInputQuote, pRspInfo, nRequestID, bIsLast):
    def OnRspQuoteAction(self, pInputQuoteAction, pRspInfo, nRequestID, bIsLast):
    def OnRspCombActionInsert(self, pInputCombAction, pRspInfo, nRequestID, bIsLast):
    def OnRspQryOrder(self, pOrder, pRspInfo, nRequestID, bIsLast):
    def OnRspQryTrade(self, pTrade, pRspInfo, nRequestID, bIsLast):

   
    def OnRspQryInvestor(self, pInvestor, pRspInfo, nRequestID, bIsLast):
    def OnRspQryTradingCode(self, pTradingCode, pRspInfo, nRequestID, bIsLast):
    def OnRspQryInstrumentMarginRate(self, pInstrumentMarginRate, pRspInfo, nRequestID, bIsLast):
    def OnRspQryInstrumentCommissionRate(self, pInstrumentCommissionRate, pRspInfo, nRequestID, bIsLast):
    def OnRspQryExchange(self, pExchange, pRspInfo, nRequestID, bIsLast):
    def OnRspQryProduct(self, pProduct, pRspInfo, nRequestID, bIsLast):
   
    def OnRspQryDepthMarketData(self, pDepthMarketData, pRspInfo, nRequestID, bIsLast):
    def OnRspQrySettlementInfo(self, pSettlementInfo, pRspInfo, nRequestID, bIsLast):
    def OnRspQryTransferBank(self, pTransferBank, pRspInfo, nRequestID, bIsLast):
    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
    def OnRspQryNotice(self, pNotice, pRspInfo, nRequestID, bIsLast):
    def OnRspQrySettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
    def OnRspQryInvestorPositionCombineDetail(self, pInvestorPositionCombineDetail, pRspInfo, nRequestID, bIsLast):
    def OnRspQryCFMMCTradingAccountKey(self, pCFMMCTradingAccountKey, pRspInfo, nRequestID, bIsLast):
    def OnRspQryEWarrantOffset(self, pEWarrantOffset, pRspInfo, nRequestID, bIsLast):
    def OnRspQryInvestorProductGroupMargin(self, pInvestorProductGroupMargin, pRspInfo, nRequestID, bIsLast):
    def OnRspQryExchangeMarginRate(self, pExchangeMarginRate, pRspInfo, nRequestID, bIsLast):
    def OnRspQryExchangeMarginRateAdjust(self, pExchangeMarginRateAdjust, pRspInfo, nRequestID, bIsLast):
    def OnRspQryExchangeRate(self, pExchangeRate, pRspInfo, nRequestID, bIsLast):
    def OnRspQrySecAgentACIDMap(self, pSecAgentACIDMap, pRspInfo, nRequestID, bIsLast):
    def OnRspQryProductExchRate(self, pProductExchRate, pRspInfo, nRequestID, bIsLast):
    def OnRspQryOptionInstrTradeCost(self, pOptionInstrTradeCost, pRspInfo, nRequestID, bIsLast):
    def OnRspQryOptionInstrCommRate(self, pOptionInstrCommRate, pRspInfo, nRequestID, bIsLast):
    def OnRspQryExecOrder(self, pExecOrder, pRspInfo, nRequestID, bIsLast):
    def OnRspQryForQuote(self, pForQuote, pRspInfo, nRequestID, bIsLast):
    def OnRspQryQuote(self, pQuote, pRspInfo, nRequestID, bIsLast):
    def OnRspQryCombInstrumentGuard(self, pCombInstrumentGuard, pRspInfo, nRequestID, bIsLast):
    def OnRspQryCombAction(self, pCombAction, pRspInfo, nRequestID, bIsLast):
    def OnRspQryTransferSerial(self, pTransferSerial, pRspInfo, nRequestID, bIsLast):
    def OnRspQryAccountregister(self, pAccountregister, pRspInfo, nRequestID, bIsLast):
    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
    def OnRspQryContractBank(self, pContractBank, pRspInfo, nRequestID, bIsLast):
    def OnRspQryParkedOrder(self, pParkedOrder, pRspInfo, nRequestID, bIsLast):
    def OnRspQryParkedOrderAction(self, pParkedOrderAction, pRspInfo, nRequestID, bIsLast):
    def OnRspQryTradingNotice(self, pTradingNotice, pRspInfo, nRequestID, bIsLast):
    def OnRspQryBrokerTradingParams(self, pBrokerTradingParams, pRspInfo, nRequestID, bIsLast):
    def OnRspQryBrokerTradingAlgos(self, pBrokerTradingAlgos, pRspInfo, nRequestID, bIsLast):
    def OnRspQueryCFMMCTradingAccountToken(self, pQueryCFMMCTradingAccountToken, pRspInfo, nRequestID, bIsLast):
    def OnRspFromBankToFutureByFuture(self, pReqTransfer, pRspInfo, nRequestID, bIsLast):
    def OnRspFromFutureToBankByFuture(self, pReqTransfer, pRspInfo, nRequestID, bIsLast):
    def OnRspQueryBankAccountMoneyByFuture(self, pReqQueryAccount, pRspInfo, nRequestID, bIsLast):
"""