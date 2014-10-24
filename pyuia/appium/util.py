from datetime import datetime

__all__ = ['get_logs']

def get_logs(driver, log_type):
    raw_logs = driver.get_log(log_type)

    logs = []
    for raw_log in raw_logs:
        timestamp_sec = raw_log['timestamp'] / 1000
        time_str = datetime.fromtimestamp(timestamp_sec).strftime('%Y-%m-%d %H:%M:%S')
        log = '%s %s' % (time_str, raw_log['message'])
        logs.append(log)

    return logs

