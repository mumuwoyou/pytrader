# encoding: UTF-8

import json
import os
import traceback

# 默认设置
from cyvn.trader.app.ctaStrategy.language.chinese import text

# 是否要使用英文
from cyvn.trader.vtGlobal import globalSetting
if globalSetting['language'] == 'english':
    from app.ctaStrategy.language.english import text
