# -*- coding:utf-8 -*-
import os
import json
from copy import copy
from datetime import datetime
import  re
import socket
import traceback

import logging
from cyvn.trader.vtGateway import *
from cyvn.trader.gateway.CtpGateway.ctpMdApi import CtpMdApi
from cyvn.trader.gateway.CtpGateway.ctpTradeApi import CtpTdApi
from cyvn.trader.vtFunction import *


def check_ctp_server(address):
    """
        检查服务器是否可用
    Args:
        address: 服务器地址及端口

    Returns:

    """
    match = re.match(r'^tcp://(.*):(\d+)$', address)
    if match:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        url, port = match.group(1), int(match.group(2))
        try:
            result = sock.connect_ex((url, port))
        except:
            traceback.print_exc()
            return False
        finally:
            sock.close()
        return result == 0
    else:
        return False


def get_available_ctp_server(addresses):
    """
        从配置的服务器列表获取可用服务器
    Args:
        addresses: 服务器列表

    Returns:
        可用服务地址
    """
    if isinstance(addresses, str):
        addresses = [addresses]
    for address in addresses:
        if check_ctp_server(address):
            return address
    return None

########################################################################
class CtpGateway(VtGateway):
    """CTP接口"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, gatewayName='CTP'):
        """Constructor"""
        super(CtpGateway, self).__init__(eventEngine, gatewayName)
        
        self.mdApi = CtpMdApi(self)     # 行情API
        self.tdApi = CtpTdApi(self)     # 交易API
        
        self.mdConnected = False        # 行情API连接状态，登录完成后为True
        self.tdConnected = False        # 交易API连接状态
        
        self.qryEnabled = False         # 循环查询

        self.requireAuthentication = False
        
    #----------------------------------------------------------------------
    def connect(self):
        """连接"""
        # 载入json文件
        fileName = self.gatewayName + '_connect.json'
        settingFilePath = getJsonPath(fileName, __file__)
        #print("connect file:",fileName)
        try:
            f = open(settingFilePath, encoding='utf-8')
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = text.LOADING_ERROR
            self.onLog(log)
            return
        
        # 解析json文件
        setting = json.load(f)
        try:
            userID = str(setting['userID']).encode('utf-8')
            password = str(setting['password']).encode('utf-8')
            brokerID = str(setting['brokerID']).encode('utf-8')
            #tdAddress = str(setting['tdAddress']).encode('utf-8')
            tdAddress = str(get_available_ctp_server(setting['tdAddress'])).encode('utf-8')
            #mdAddress = str(setting['mdAddress']).encode('utf-8')
            mdAddress = str(get_available_ctp_server(setting['mdAddress'])).encode(('utf-8'))
            #print("config:", userID, password, brokerID, tdAddress, mdAddress)
            # 如果json文件提供了验证码
            if 'authCode' in setting: 
                authCode = str(setting['authCode']).encode('utf-8')
                userProductInfo = str(setting['userProductInfo']).encode('utf-8')
                self.tdApi.requireAuthentication = True
            else:
                authCode = EMPTY_BYTE
                userProductInfo = EMPTY_BYTE

        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = text.CONFIG_KEY_MISSING
            self.onLog(log)
            return            
        
        # 创建行情和交易接口对象
        self.mdApi.connect(userID, password, brokerID, mdAddress)
        self.tdApi.connect(userID, password, brokerID, tdAddress, authCode, userProductInfo)
        
        # 初始化并启动查询
        self.initQuery()
    
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""
        self.mdApi.subscribe(subscribeReq)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        return self.tdApi.sendOrder(orderReq)
        
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        self.tdApi.cancelOrder(cancelOrderReq)
        
    #----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户资金"""
        self.tdApi.qryAccount()
        
    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.tdApi.qryPosition()

    #----------------------------------------------------------------------
    def qryPositionDetail(self):
        """查询持仓"""
        self.tdApi.qryPositionDetail()
        
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        if self.mdConnected:
            self.mdApi.close()
        if self.tdConnected:
            self.tdApi.close()
        
    #----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryAccount, self.qryPosition, self.qryPositionDetail]
            
            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 2         # 查询触发点
            self.qryNextFunction = 0    # 上次运行的查询函数索引
            
            self.startQuery()
    
    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1
        
        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0
            
            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()
            
            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
    
    #----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)
    
    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled




