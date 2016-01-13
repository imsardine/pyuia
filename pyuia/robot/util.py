import logging, os.path as path, time

__all__ = ['in_context', 'get_current_test_case', 'log_screenshot', 'log_text', 'is_test_failed']
_log = logging.getLogger(__name__)

try:
    from robot.running.context import EXECUTION_CONTEXTS as contexts
    in_context = True if contexts.current else False
except ImportError:
    in_context = False

try:
    from robot.libraries.BuiltIn import BuiltIn
    _builtin = BuiltIn()
except ImportError:
    _builtin = None

def is_test_failed():
    status = _builtin.get_variable_value('${TEST_STATUS}')
    if status == 'FAIL': return True
    assert status in ['PASS', None], status
    return False

def get_current_test_case():
    """Return a 2-tuple which uniquely identifying the current test case.

       Returns: 2-tuple (suite_source, test_name), where suite_source is an
                absolute path to the suite file or directory.
    """
    return (_builtin.get_variable_value('${SUITE_SOURCE}'),
            _builtin.get_variable_value('${TEST_NAME}'))

def _robot_logger_of_level(level):
    # standard levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    # robot levels: TRACE, DEBUG, INFO, WARN, ERROR
    from robot.api import logger as robot_logger
    if level == logging.DEBUG:
        return robot_logger.debug
    elif level == logging.INFO:
        return robot_logger.info
    elif level == logging.WARNING:
        return robot_logger.warn
    elif level in (logging.ERROR, logging.CRITICAL):
        return robot_logger.error
    else:
        assert False, level

def log_screenshot(png, msg='SCREENSHOT', prefix='screenshot_', level=logging.DEBUG):
    filename = '%s%s.png' % (prefix, int(time.time() * 1000))
    pathname = path.join(_get_log_dir(), filename)
    with open(pathname, 'wb') as f:
        f.write(png)
    html = '<a href="%s" target="_blank"><img src="%s" width="200"></a>' % (filename, filename)

    msg = '%s<br/>%s' % (msg, html) # TODO: HTML encode msg
    _robot_logger_of_level(level)(msg, html=True)

def log_text(text, msg='TEXT', prefix='text', suffix='.txt', level=logging.DEBUG):
    from robot.api import logger as robot_logger

    filename = '%s%s%s' % (prefix, int(time.time() * 1000), suffix)
    pathname = path.join(_get_log_dir(), filename)
    with open(pathname, 'wb') as f:
	f.write(text.encode('utf-8'))
    html = '<a href="%s" target="_blank">%s</a>' % (filename, filename)

    msg = '%s: %s' % (msg, html) # TODO: HTML encode msg
    _robot_logger_of_level(level)(msg, html=True)

def _get_log_dir(): # TODO: one-time calculation
    variables = _builtin.get_variables()
    outdir = variables['${OUTPUT_DIR}']
    log = variables['${LOGFILE}'] # relative to the output dir
    logdir = path.dirname(log) if log != 'NONE' else '.'
    return path.abspath(path.join(outdir, logdir))

