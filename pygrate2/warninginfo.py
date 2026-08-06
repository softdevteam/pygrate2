class WarningInfo(object):
    def __init__(self, filename, lineno, warning_type, msg):
        self.filename = filename
        self.lineno = lineno
        self.warning_type = warning_type
        self.msg = msg

    def __str__(self):
        return '{}:{}: {}Warning: {}'.format(self.filename, self.lineno, self.warning_type, self.msg)
