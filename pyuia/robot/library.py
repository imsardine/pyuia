import logging, inspect
from robot.utils import ConnectionCache
from pyuia import PageObject, get_page_object
from util import is_test_failed, log_screenshot, log_text, in_context as in_robot_context

__all__ = ['BaseAppLibrary']
_logger = logging.getLogger(__name__)

def _state_capturing_decorator(method):
    def decorator(*args, **kwargs):
        name = method.__name__
        accessor = any(name.startswith(prefix) or name == prefix for prefix in ['is_', 'get_', 'should_be_'])
        self = args[0] # the keyword library itself

        self._capture_state()
        try:
            result = method(*args, **kwargs)

            # if the the result is a page object, update the current page.
            if isinstance(result, PageObject):
                self._current_page = result
        except Exception as err:
            self._capture_state(after=True, err=err)
            raise

        if not accessor: # efficiency
            self._capture_state(after=True)
        return result

    return decorator

class _StateCapturing(type):

      def __new__(cls, clsname, bases, attrs):
          for name, obj in attrs.items():
              if not (inspect.isroutine(obj) and not name.startswith('_')): continue
              if name in ['open_app', 'close_app', 'close_all_apps', 'switch_device']: continue
              attrs[name] = _state_capturing_decorator(obj)
          return type.__new__(cls, clsname, bases, attrs)

class BaseAppLibrary(object):

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    if in_robot_context:
        __metaclass__ = _StateCapturing

    def __init__(self):
        self._cache = ConnectionCache()

    def open_app(self, device_id, alias=None):
        _logger.info('Open app; device ID = [%s], alias = [%s])', device_id, alias)

        # init context and install delegates
        context = self._init_context(device_id)
        context._log_screenshot_delegate = self._log_screenshot_delegate
        context._log_page_source_delegate = self._log_page_source_delegate
        context.logs_all = [] # accumulate logs of each step

        log_text('\n'.join(context.get_initial_logs()), 'APP LOGS (Initial)', 'app_logs_initial_', '.log')
        return self._cache.register(RFConnectionCache(context), alias)

    def _init_context(self):
        raise NotImplementedError()

    def _log_screenshot_delegate(self, msg, *args, **kwargs):
        msg = msg % args
        level = kwargs['level'] if 'level' in kwargs else logging.INFO
        page = kwargs['page'] if 'page' in kwargs else None

        if page: msg += ' (%s)' % page.__class__.__name__
        log_screenshot(self._current_context.take_screenshot_as_png(), msg, level=level)

    def _log_page_source_delegate(self, msg, *args, **kwargs):
        msg = msg % args
        level = kwargs['level'] if 'level' in kwargs else logging.INFO
        page = kwargs['page'] if 'page' in kwargs else None

        if page: msg += ' (%s)' % page.__class__.__name__
        source, ext = self._current_context.dump_page_source()
        log_text(source, msg, prefix='page_source_', suffix='.%s' % ext, level=level)

    def close_app(self):
        self._cache.current.close()

    def close_all_apps(self):
        self._cache.close_all()

    def switch_device(self, alias_or_index):
        self._cache.switch(alias_or_index)

    def _capture_state(self, after=False, err=None):
        # To increase efficiency, screenshots are no longer taken automatically.
        # Developers should explicitly do that AFTER the UI has been changed.
        if not after: return

        context = self._current_context
        try:
            if after:
                logs_step = context.get_new_logs()
                context.logs_all.extend(logs_step)
                log_text('\n'.join(logs_step), 'APP LOGS (Step)', 'app_logs_step_', '.log')
        except:
            _logger.warning('Fail to capture state.', exc_info=True)

    @property
    def _current_context(self):
        return self._cache.current._context

    @property
    def _current_page(self):
        return self._cache.current._context.current_page

    @_current_page.setter
    def _current_page(self, page):
        self._cache.current._context.current_page = page

class RFConnectionCache(object):

    def __init__(self, context):
        self._context = context

    def close(self):
        # all statements suppress possible errors, or other sessions won't be closed.
        self._capture_state()
        self._context.quit()

    def _capture_state(self):
        failed = None
        context = self._context
        try:
            failed = is_test_failed()
            msg = 'APP LOGS (about to quit, failed = %s)' % failed

            context.logs_all.extend(context.get_new_logs())
            log_text('\n'.join(context.logs_all), msg, 'app_logs_all_', '.log')
            if not failed: return

            context.log_page_source('PAGE SOURCE (Failed)')
            context.log_screenshot('SCREENSHOT (Failed)')
        except Exception as e:
            _logger.warning('Fail to capture state. (failed = %s)', failed, exc_info=True)

