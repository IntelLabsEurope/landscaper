import subprocess
from datetime import datetime
LOGF = '/collector_log/landscaper.log'
LOG_BATCH_LINE_COUNT = 50


class LogApi:

    def __init__(self):
        pass

    def get_log(self, from_tm=None):
        raw_log = subprocess.check_output(['tail', '-n', str(LOG_BATCH_LINE_COUNT), LOGF])
        lines = raw_log.splitlines()
        for i in range(0, len(lines)):
            line = lines[i]
            tm = line[1:24]
            tm = datetime.strptime(tm, '%Y-%m-%d %H:%M:%S %Z').isoformat()
            typ = line[27:31]
            desc = line[35:len(line)]
            line = {'log_time': tm, 'log_type': typ, 'log_text': desc}
            lines[i] = line
        lines.sort(key=sort_log, reverse=True)
        if from_tm:
            lines = filter_log(lines, from_tm)
        return lines


def sort_log(line):
    return line['log_time']


def filter_log(lines, tm):
    f_log = []
    for line in lines:
        if line['log_time'] > tm:
            f_log.append(line)
        else:
            break
    return f_log