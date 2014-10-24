import time, logging
from .exceptions import TimeoutError, ElementNotFoundError

__all__ = ['PageObject', 'get_page_object']
_logger = logging.getLogger(__name__)

_page_singletons = {} # cache

def get_page_object(page_class, context):
    fqcn = '%s.%s' % (page_class.__module__, page_class.__name__)
    _logger.debug('Get page object; FQCN = %s', fqcn)
    if fqcn in _page_singletons:
        cache = _page_singletons[fqcn]
        if cache._context is context:
            _logger.debug('Cached, and the context remains unchanged.')
            return cache
        else:
            _logger.debug('Cached, but the context is invalid.')

    page = page_class(context)
    _page_singletons[fqcn] = page
    return page

def _is_iterable(obj):
    try:
       iter(obj)
       return True
    except TypeError:
       return False

def _to_iterable(obj):
    return obj if _is_iterable(obj) else (obj,)

_WAIT_INTERVAL = 1

_WAIT_TIMEOUT = 60

_WARN_TIMEOUT = 10

_NOT_FOUND_EXCEPTIONS = (ElementNotFoundError,)

class PageObject(object):

    def __init__(self, context, not_found_exceptions):
        self._context = context

        exceptions = list(_NOT_FOUND_EXCEPTIONS)
        if not_found_exceptions:
            try:
                exceptions.extend(not_found_exceptions)
            except TypeError: # not iterable
                exceptions.append(not_found_exceptions)
        self._not_found_exceptions = tuple(exceptions)

    def _page_object(self, page_class, wait_for_loaded=True):
        """Instantiate a page object."""
        page = get_page_object(page_class, self._context)
        if wait_for_loaded: page.wait_for_page_loaded()
        return page

    def wait_for_page_loaded(self, timeout_warn=_WARN_TIMEOUT, timeout=_WAIT_TIMEOUT):
        start_time = time.time()
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout

        while True:
            try:
                self.assert_on_this_page()
                break
            except AssertionError:
                if time.time() > timeout_warn:
                    self._log_screenshot(
                        'Wait for page loaded. Time elapsed = [%s]s.',
                        time.time() - start_time,
                        level=logging.WARN)

                time.sleep(_WAIT_INTERVAL)
                if time.time() > timeout: raise
        if hasattr(self, '_wait_for_idle'):
            self._log_screenshot('Already on certain page then wait for idle.')
            self._wait_for_idle()
        return self

    def assert_on_this_page(self): pass

    def _log_screenshot(self, msg, *args, **kwargs):
        kwargs['page'] = self
        self._context.log_screenshot(msg, *args, **kwargs)

    def _log_page_source(self, msg, *args, **kwargs):
        kwargs['page'] = self
        self._context.log_page_source(msg, *args, **kwargs)

    def _assert_present(self, locators, handlers=None, check_visibility=False):
        single_loc = not _is_iterable(locators)
        locators = _to_iterable(locators)
        elements = []

        for locator in locators:
            try:
                element = locator()
            except self._not_found_exceptions as e:
                _logger.debug(
                    'Assert ALL present. The locator (%s) did not resolve to '
                    'an element.', locator, exc_info=True)
                element = None
            if not element:
                _consult_handlers(handlers)
                assert False, locator # None or empty sequence

            if check_visibility and not self._is_displayed(element):
                _consult_handlers(handlers)
                assert False, locator
            elements.append(element)

        return elements[0] if single_loc else elements

    def _assert_visible(self, locators, handlers=None):
        return self._assert_present(locators, handlers, check_visibility=True)

    def _assert_any_present(self, locators, handlers=None, check_visibility=False):
        locators = _to_iterable(locators)

        for locator in locators:
            try:
                element = locator()
            except self._not_found_exceptions as e:
                _logger.debug(
                    'Assert ANY present. The locator (%s) did not resolve to '
                    'an element.', locator, exc_info=True)
                element = None
            if not element: continue # None or empty sequence

            if check_visibility and not self._is_displayed(element): continue
            return element

        _consult_handlers(handlers)
        assert False, locators

    def _assert_any_visible(self, locators, handlers=None):
        return self._assert_any_present(locators, handlers, check_visibility=True)

    def _wait_present(self, locators, timeout_warn=_WARN_TIMEOUT, handlers=None,
                      timeout=_WAIT_TIMEOUT, check_visibility=False):
        start_time = time.time()
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        single_loc = not _is_iterable(locators)
        locators = _to_iterable(locators)

        while True:
            elements = []
            for locator in locators:
                try:
                    element = locator()
                except self._not_found_exceptions as e:
                    _logger.debug(
                        'Wait ALL present. The locator (%s) did not resolve to '
                        'an element.', locator, exc_info=True)
                    element = None
                if not element: break # None or empty sequence

                if check_visibility and not self._is_displayed(element): break
                elements.append(element)

            if len(elements) == len(locators):
                return elements[0] if single_loc else elements

            if time.time() > timeout_warn:
                self._log_screenshot(
                    'Wait ALL elements to be present. locators = %s, '
                    'check_visibility = [%s], time elapsed = [%s]s.',
                    locators, check_visibility, time.time() - start_time,
                    level=logging.WARN)
            _consult_handlers(handlers)

            time.sleep(_WAIT_INTERVAL)
            if time.time() > timeout:
                raise TimeoutError(
                    'Wait ALL elements to be present. locators = %s, '
                    'check_visibility = [%s], time elapsed = [%s]s.' %
                    (locators, check_visibility, time.time() - start_time))

    def _wait_visible(self, locators, timeout_warn=_WARN_TIMEOUT, handlers=None, timeout=_WAIT_TIMEOUT):
        return self._wait_present(locators, timeout_warn, handlers, timeout, check_visibility=True)

    def _wait_any_present(self, locators, timeout_warn=_WARN_TIMEOUT, handlers=None,
                          timeout=_WAIT_TIMEOUT, check_visibility=False):
        start_time = time.time()
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        locators = _to_iterable(locators)

        while True:
            for locator in locators:
                try:
                    element = locator()
                except self._not_found_exceptions as e:
                    _logger.debug(
                        'Wait ANY present. The locator (%s) did not resolve to '
                        'an element.', locator, exc_info=True)
                    element = None
                if not element: continue # None or empty sequence

                if check_visibility and not self._is_displayed(element): continue
                return element

            if time.time() > timeout_warn:
                self._log_screenshot(
                    'Wait ANY present. locators = %s, time elapsed = [%s]s.',
                    locators, time.time() - start_time, level=logging.WARN)
            _consult_handlers(handlers)

            time.sleep(_WAIT_INTERVAL)
            if time.time() > timeout:
                raise TimeoutError(
                    'Wait ANY elements to be present. locators = %s, '
                    'check_visibility = [%s], time elapsed = [%s]s.' %
                    (locators, check_visibility, time.time() - start_time))

    def _wait_any_visible(self, locators, timeout_warn=_WARN_TIMEOUT, handlers=None,
                          timeout=_WAIT_TIMEOUT):
        return self._wait_any_present(locators, timeout_warn, handlers, timeout, check_visibility=True)

    def _wait_absent(self, locators, timeout_warn=_WARN_TIMEOUT, minwait=3,
                     handlers=None, timeout=_WAIT_TIMEOUT, check_visibility_only=False):
        start_time = time.time()
        timeout_appear = start_time + minwait
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        locators = _to_iterable(locators)

        while True:
            # to avoid the situation that elements are absent simply because
            # other elements such as error dialogs are displayed.
            _consult_handlers(handlers)
            any_invalid = False
            for locator in locators:
                try:
                    element = locator()
                except self._not_found_exceptions as e:
                    _logger.debug(
                        'Wait ALL absent. The locator (%s) did not resolve to '
                        'an element.', locator, exc_info=True)
                    element = None
                if not element: continue

                if not check_visibility_only or self._is_displayed(element):
                    any_invalid = True
                    break

            # wait for at least 'minwait' seconds to make sure target
            # element(s) won't appear at this time.
            if not any_invalid and time.time() > timeout_appear: return
            if time.time() > timeout_warn:
                self._log_screenshot(
                    'Wait ALL elements to be absent. locators = %s, '
                    'check_visibility_only = [%s], time elapsed = [%s]s.',
                    locators, check_visibility_only, time.time() - start_time, 
                    level=logging.WARN)

            time.sleep(_WAIT_INTERVAL)
            if time.time() > timeout:
                raise TimeoutError(
                    'Wait ALL elements to be absent. locators = %s, '
                    'check_visibility_only = [%s], time elapsed = [%s]s.' %
                    (locators, check_visibility_only, time.time() - start_time))

    def _wait_invisible(self, locators, timeout_warn=_WARN_TIMEOUT, minwait=3,
                        handlers=None, timeout=_WAIT_TIMEOUT):
        self._wait_absent(locators, timeout_warn, minwait, handlers, timeout, check_visibility_only=True)

    def _handle_conditional_views(self, handlers, duration=5):
        timeout = time.time() + duration
        while True:
            _consult_handlers(handlers)
            if time.time() > timeout: break

def _consult_handlers(handlers):
    if handlers is None: return

    for locator, handler in handlers.items():
        try:
            element = locator()
        except self._not_found_exceptions as e:
            _logger.debug(
                'Consult handlers. The locator (%s) did not resolve to an element.',
                locator, exc_info=True)
            element = None
        if not element: continue

        handler(element)

