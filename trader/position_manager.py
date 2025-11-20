"""
Position Manager Module
重點 : signal True != place order
Avoid repeat order
"""

class PositionManager:
    def __init__(self):
        self.active = False
        self.qty = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        self.stop_loss = None
        self.take_profit = None

    def open_long(self, price, qty, timestamp, sl=None, tp=None):
        """建立多頭部位"""
        self.active = True
        self.qty = qty
        self.entry_price = price
        self.entry_time = timestamp
        self.stop_loss = sl
        self.take_profit = tp

    def should_exit(self, price, exit_signal=False):
        """判斷是否需要平倉"""

        # 1. 策略 Exit 訊號
        if exit_signal:
            return True

        # 2. 觸發停損
        if self.stop_loss is not None and price <= self.stop_loss:
            return True

        # 3. 觸發停利
        if self.take_profit is not None and price >= self.take_profit:
            return True

        return False

    def close_position(self):
        """平倉後清空部位"""
        self.active = False
        self.qty = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        self.stop_loss = None
        self.take_profit = None
