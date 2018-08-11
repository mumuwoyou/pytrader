#!/usr/bin/python3
# -*- coding:utf-8 -*-

from cyvn.trader.vtFunction import loadIconPath
from cyvn.trader.eventEngine import EventEngine2, EventEngine
from cyvn.trader.gateway.CtpGateway.ctpGateway import CtpGateway
#from app import ctaStrategy
from cyvn.trader.vtEngine import MainEngine
from cyvn.trader.uiMainWindow import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui
#----------------------------------------------------------------------
def main():
    """主程序入口"""
    # 创建Qt应用对象
    import sys
    app = QApplication(sys.argv)

    app.setWindowIcon(QtGui.QIcon(loadIconPath('vnpy.ico')))
    #qApp = createQApp()

    # 创建事件引擎
    ee = EventEngine()

    # 创建主引擎
    me = MainEngine(ee)

    # 添加交易接口
    #ctpGateway = CtpGateway(ee, gatewayName='CTP')
    me.addGateway('CTP')
    #me.connect('CTP')
    #while True:
    #    i = 10
    #me.addGateway(oandaGateway)
    #me.addGateway(ibGateway)
    #me.addGateway(huobiGateway)
    #me.addGateway(okcoinGateway)

   
    # 添加上层应用
    #me.addApp(riskManager)
    #me.addApp(ctaStrategy)
    #me.addApp(spreadTrading)

    # 创建主窗口
    mw = MainWindow(me, ee)
    mw.showMaximized()

    # 在主线程中启动Qt事件循环
    #sys.exit(qApp.exec_())
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


