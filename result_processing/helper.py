def interval_include(interval1, interval2):
    if (interval1[0] <= interval2[0]) and (interval1[1] >= interval2[1]):
        return True
    else:
        return False

class IntervalTree(object):
    def __init__(self, interval, maximum, result):
        self.interval = interval
        self.result = result
        self.maximum = interval[1]
        self.left = None
        self.right = None
    
    def search(self, interval):
        if interval_include(self.interval, interval):
            return self.result
        elif self.left and (self.left.maximum > interval[0]):
            return self.left.search(interval)
        elif self.right:
            return self.right.search(interval)
        else:
            return None