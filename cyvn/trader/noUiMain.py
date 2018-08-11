#!/usr/bin/python3
# -*- coding:utf-8 -*-


import signal
import os
import sys

from cyvn.trader.eventEngine import EventEngine2, EventEngine
#from gateway.ctpGateway import CtpGateway
import cyvn.trader.gateway
from cyvn.trader.app import ctaStrategy
from cyvn.trader.vtEngine import MainEngine
from PyQt5.QtCore import QCoreApplication


me = None #主引擎

def processSignal(signum, stack):
    #print('Received:', signum)
    #if me is not None:
    global me
    me.exit()
    #第一次无法终止
    #if signum == signal.SIGINT:
    sys.exit(1)



#----------------------------------------------------------------------
def main():
    """主程序入口"""
    
 
    # 注册信号处理程序
    signal.signal(signal.SIGUSR1, processSignal)
    signal.signal(signal.SIGUSR2, processSignal)
    signal.signal(signal.SIGINT, processSignal)

    # 创建Qt应用对象
   
    app = QCoreApplication(sys.argv)

    # 创建事件引擎
    ee = EventEngine()

    # 创建主引擎
    global me
    me = MainEngine(ee)

    # 添加交易接口
    #ctpGateway = CtpGateway(ee, gatewayName='CTP')
    me.addGateway(gateway.gatewayName)
    #me.dbConnect()
    #创建策略引擎
    ce = ctaStrategy.appEngine(me, ee)
    ce.loadSetting()
    ce.initAll()
    ce.startAll() 

    # 添加上层应用
    #me.addApp(riskManager)
    me.addApp(ctaStrategy)
    #me.addApp(spreadTrading)  
  
    me.connect(gateway.gatewayName)
    

    # 在主线程中启动Qt事件循环
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


