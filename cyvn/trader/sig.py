import signal
import os
import time
import sys

def receive_signal(signum, stack):
    print('Received:', signum)
    if signum == signal.SIGINT:
        sys.exit(1)


# 注册信号处理程序
signal.signal(signal.SIGUSR1, receive_signal)
signal.signal(signal.SIGUSR2, receive_signal)

signal.signal(signal.SIGINT, receive_signal)

# 打印这个进程的PID方便使用kill传递信号

print('My PID is:', os.getpid())

# 等待信号，有信号发生时则调用信号处理程序
while True:
    print ('Waiting...')
    time.sleep(3)