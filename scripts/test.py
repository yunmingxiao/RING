# import time
# import sched


# # 初始化scheduler类
# # 第一个参数是一个可以返回时间戳的函数，第二个参数可以在定时未到达之前阻塞。
# s = sched.scheduler(time.time, time.sleep)


# # 被周期性调度的任务
# def task():
#     print("run time: {}".format(int(time.time())))


# def perform(inc):
#     s.enter(inc, 0, perform, (inc,))
#     task()


# def main(inc=3):
#     s.enter(0, 0, perform, (inc,))
#     s.run()
#     print('here')


# if __name__ == "__main__":
#     main()


# from datetime import datetime
# import time
# from threading import Timer
# # 打印时间函数
# class Test():
#     def __init__(self):
#         self.printTime(3)

#     def __del__(self):
#         print('del')

#     def printTime(self, n):
#         print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#         t = Timer(n, self.printTime, (n,))
#         t.start()
# # 2s
# test = Test()
# test.__del__()
# print('finish')
# time.sleep(5)
# test = Test()


print('some test')
print('some other test')