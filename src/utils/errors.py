class EventError(Exception):
    pass
class EventResultsError(EventError):
    def __init__(self):
        EventError.__init__(self, "Failed to load results")
class EventNotEnoughArgsError(EventError):
    def __init__(self, n):
        EventError.__init__(self, "Not enough arguments (minimum %d)" % n)
class EventUsageError(EventError):
    def __init__(self, usage):
        EventError.__init__(self, "Not enough arguments, usage: %s" % usage)

