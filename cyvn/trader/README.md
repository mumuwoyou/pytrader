# cyvn
基于vnpy的cython版本
首先感谢vnpy 和 [https://github.com/lovelylain/pyctp](https://github.com/lovelylain/pyctp)项目,这个项目将vnpy的上层以及pyctp的底层ctp库做了合并，使用上不再依赖boost-python, 部署更加方便,整个项目遵循MIT协议，本项目保留了原项目的注释。如以上项目作者有异议，请联系本人。pyctp的源码将会稍后上传。 windows版本因存在dbm error，将于晚些时候发布。

本项目基于python3，编译平台linux mint 18.1 
使用:
按照所需要的依赖库: pip install pymongo psutil PyQt5 TA-Lib 
下载后进入源码目录: python3 uiMain.py (GUI版本) 或者python3 noUiMain.py 

注意:
 **目前的版本还有不少bug, 请勿在实盘中使用** 。