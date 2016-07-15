import logging, inspect
from robot.utils import ConnectionCache
from pyuia import PageObject, get_page_object
from util import is_test_failed, log_screenshot, log_text, in_context as in_robot_context

__all__ = ['BaseAppLibrary']
_logger = logging.getLogger(__name__)

def _state_capturing_decorator(method):
    def decorator(*args, **kwargs):
        name = method.__name__
        # accessor = any(name.startswith(prefix) or name == prefix for prefix in ['is_', 'get_', 'should_be_'])
        accessor = False
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
          white_list = [
              'open_session',
              'close_session',
              'close_all_sessions',
              'switch_device',
              'open_app',
              'close_app',
          ]

          for name, obj in attrs.items():
              if not (inspect.isroutine(obj) and not name.startswith('_')): continue
              if name in white_list: continue
              attrs[name] = _state_capturing_decorator(obj)
          return type.__new__(cls, clsname, bases, attrs)

class BaseAppLibrary(object):

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    if in_robot_context:
        __metaclass__ = _StateCapturing

    def __init__(self):
        self._cache = ConnectionCache()

    def open_session(self, device_id, alias=None):
        """Open a session.

        ``device_id`` is an identifier for looking up configurations of a specific device.

        The optional ``alias`` provided here can be used to switch between sessions/devices later.
        See `Switch Device` for more details.

        """
        _logger.info('Open session; device ID = [%s], alias = [%s])', device_id, alias)
        # init context and install delegates
        context = self._init_context(device_id)
        context._log_screenshot_delegate = self._log_screenshot_delegate
        context._log_page_source_delegate = self._log_page_source_delegate
        self._cache.register(RFConnectionCache(context), alias)

    def open_app(self, reset=None):
        """Open the app.

        To reset app state prior to opening the app, pass a non-empty string to ``reset`` argument.

        Examples:

        | Open App | reset | # reset app state        |
        | Open App |       | # do not reset app state |

        """
        msg = 'App logs (initial)'
        context = self._current_context
        context.open_app(bool(reset))

        context.logs_all = [] # accumulate logs of each step
        log_text('\n'.join(context.get_initial_logs()), msg, 'app_logs_initial_', '.log', level=logging.INFO)

    def _init_context(self):
        raise NotImplementedError()

    def _log_screenshot_delegate(self, msg, *args, **kwargs):
        level = kwargs['level'] if 'level' in kwargs else logging.DEBUG
        if not _logger.isEnabledFor(level):
            return

        page = kwargs['page'] if 'page' in kwargs else None
        msg = msg % args

        if page: msg += ' (%s)' % page.__class__.__name__
        log_screenshot(self._current_context.take_screenshot_as_png(), msg, level=level)

    def _log_page_source_delegate(self, msg, *args, **kwargs):
        level = kwargs['level'] if 'level' in kwargs else logging.DEBUG
        if not _logger.isEnabledFor(level):
            return

        page = kwargs['page'] if 'page' in kwargs else None
        msg = msg % args

        if page: msg += ' (%s)' % page.__class__.__name__
        source, ext = self._current_context.dump_page_source()
        log_text(source, msg, prefix='page_source_', suffix='.%s' % ext, level=level)

    def close_session(self):
        """Terminate current session."""
        self._cache.current.close()

    def close_all_sessions(self):
        """Terminate all open sessions."""
        self._cache.close_all()

    def close_app(self):
        """Close the app."""
        self._cache.current.close_app()

    def switch_device(self, alias):
        """Switch between sessions/devices using alias.

        Examples:

        | Open App      | A | # current session/device is A      |
        | Open App      | B | # current session/device becomes B |
        | Switch Device | A | # switch back to A                 |

        """
        self._cache.switch(alias)

    def _capture_state(self, after=False, err=None):
        # To increase efficiency, screenshots are no longer taken automatically.
        # Developers should explicitly do that AFTER the UI has been changed.
        if not after: return

        failed = bool(err)
        try:
            context = self._current_context
            msg = 'App logs (step, keyword failed? %s)' % failed

            logs_step = context.get_new_logs()
            context.logs_all.extend(logs_step)
            log_text('\n'.join(logs_step), msg, 'app_logs_step_', '.log', level=logging.INFO)
            if not failed: return

            context.log_page_source('Page source', level=logging.INFO)
            context.log_screenshot('Screenshot', level=logging.INFO)
        except:
            _logger.warning('Fail to capture state. (keyword failed = %s)', failed, exc_info=True)

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
        self._context.quit()

    def close_app(self):
        # all statements suppress possible errors, or other sessions won't be closed.
        self._capture_state()
        self._context.close_app()

    def _capture_state(self):
        failed = None

        try:
            failed = is_test_failed()
            context = self._context
            msg = 'App logs (about to quit, test failed? %s)' % failed

            context.logs_all.extend(context.get_new_logs())
            log_text('\n'.join(context.logs_all), msg, 'app_logs_all_', '.log', level=logging.INFO)
            if not failed: return

            context.log_page_source('Page source (test failed)', level=logging.INFO)
            context.log_screenshot('Screenshot (test failed)', level=logging.INFO)
        except Exception as e:
            _logger.warning('Fail to capture state. (test failed = %s)', failed, exc_info=True)

