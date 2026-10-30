# -*- coding: utf-8 -*-
"""进程内事件总线：HTTP 线程 -> Qt 界面线程 的单向通知。

服务器（工作线程）收到教师消息后 emit 事件，
界面层订阅后放进队列，再由 QTimer 在主线程消费，避免跨线程操作控件。
"""
import threading

from . import util


class EventHub(object):
    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers = []

    def subscribe(self, callback):
        if callback is None:
            return
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback):
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def emit(self, event):
        with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            try:
                callback(event)
            except Exception as exc:
                util.LOG.warn("事件回调执行失败：{}".format(exc))
