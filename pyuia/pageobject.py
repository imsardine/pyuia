import time, logging
from .exceptions import TimeoutError, ElementNotFoundError

__all__ = ['PageObject', 'get_page_object', 'cacheable']
_logger = logging.getLogger(__name__)

_page_singletons = {} # cache

def get_page_object(page_class, context):
    fqcn = '%s.%s' % (page_class.__module__, page_class.__name__)
    _logger.debug('Get page object; FQCN = %s', fqcn)
    if fqcn in _page_singletons:
        cache = _page_singletons[fqcn]
        if cache._context is context:
            _logger.debug('Cached, and the context remains unchanged.')
            cache._invalidate_elements_cache()

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

_NOT_FOUND_EXCEPTIONS = (ElementNotFoundError,)

_ELEMENTS_CACHE_ATTR = '_pyuia_elements_cache'

def cacheable(lookup, cache_none=True):
    def func(self):
        if not hasattr(self, _ELEMENTS_CACHE_ATTR):
            setattr(self, _ELEMENTS_CACHE_ATTR, {}) # {callable_id: element(s)}
        cache = getattr(self, _ELEMENTS_CACHE_ATTR)

        key = id(lookup)
        if key not in cache:
            result = lookup(self)
            if result is None and not cache_none: return
            cache[key] = result
        return cache[key]

    return func

class PageObject(object):

    _WAIT_INTERVAL = 0
    _WARN_TIMEOUT = 5
    _WAIT_TIMEOUT = 10
    _PAGE_WARN_TIMEOUT = 5
    _PAGE_WAIT_TIMEOUT = 10
    
    def __init__(self, context, not_found_exceptions):
        self._context = context

        exceptions = list(_NOT_FOUND_EXCEPTIONS)
        if not_found_exceptions:
            try:
                exceptions.extend(not_found_exceptions)
            except TypeError: # not iterable
                exceptions.append(not_found_exceptions)
        self._not_found_exceptions = tuple(exceptions)

        exceptions.append(AssertionError)
        self._page_assertion_exceptions = tuple(exceptions)

    def _go_to(self, page_class):
        """Instantiate a page object."""
        page = get_page_object(page_class, self._context)
        page._from_page_class = self.__class__

        page.wait_for_page_loaded(self.__class__)
        return page

    def _back_to(self, page_class=None):
        if not page_class:
            if not hasattr(self, '_from_page_class'):
                raise RuntimeError("_back_to(page_class) don't know where to go. You can explicitly specify "
                                   "'page_class' or implement page transition with _go_to(page_class).")
            page_class = self._from_page_class
        page = get_page_object(page_class, self._context)

        page.wait_for_page_loaded(self.__class__)
        return page

    def _invalidate_elements_cache(self):
        if hasattr(self, _ELEMENTS_CACHE_ATTR):
            delattr(self, _ELEMENTS_CACHE_ATTR)

    def wait_for_page_loaded(self, from_page_class=None, timeout_warn=None, timeout=None):
        timeout_warn = timeout_warn or self._PAGE_WARN_TIMEOUT
        timeout = timeout or self._PAGE_WAIT_TIMEOUT

        start_time = time.time()
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        handlers = self._get_page_entry_handlers(from_page_class)

        warned = False
        while True:
            try:
                self._invalidate_elements_cache()
                self.assert_on_this_page(from_page_class)
                break
            except self._page_assertion_exceptions:
                if not warned and time.time() > timeout_warn:
                    self._log_screenshot(
                        'Wait for page loaded. Time elapsed = [%s]s.',
                        time.time() - start_time,
                        level=logging.WARN)
                    warned = True

                handlers = self._consult_handlers(handlers)
                time.sleep(self._WAIT_INTERVAL)
                if time.time() > timeout: raise

        self._log_screenshot('Already on the page.')

        # return True to indicate UI changed.
        if self._on_page_entry(from_page_class):
            self._log_screenshot('Page loaded.')

        return self

    def _get_page_entry_handlers(self, from_page_class): pass

    def assert_on_this_page(self, from_page_class): pass

    def _on_page_entry(self, from_page_class):
        """To put the page in a known state."""
        pass

    def _log_screenshot(self, msg, *args, **kwargs):
        kwargs['page'] = self
        self._context.log_screenshot(msg, *args, **kwargs)

    def _log_page_source(self, msg, *args, **kwargs):
        kwargs['page'] = self
        self._context.log_page_source(msg, *args, **kwargs)

    def _assert_present(self, locators, check_visibility=False):
        single_loc = not _is_iterable(locators)
        locators = _to_iterable(locators)
        elements = []

        for locator in locators:
            try:
                element = locator()
            except self._not_found_exceptions as e:
                _logger.debug(
                    'Assert ALL present. The locator (%s) did not resolve to '
                    'an element.', locator)
                element = None
            if not element:
                assert False, locator # None or empty sequence

            if check_visibility and not self._is_displayed(element):
                assert False, locator
            elements.append(element)

        return elements[0] if single_loc else elements

    def _assert_visible(self, locators):
        return self._assert_present(locators, check_visibility=True)

    def _assert_any_present(self, locators, check_visibility=False):
        locators = _to_iterable(locators)

        for locator in locators:
            try:
                element = locator()
            except self._not_found_exceptions as e:
                _logger.debug(
                    'Assert ANY present. The locator (%s) did not resolve to '
                    'an element.', locator)
                element = None
            if not element: continue # None or empty sequence

            if check_visibility and not self._is_displayed(element): continue
            return element

        assert False, locators

    def _assert_any_visible(self, locators):
        return self._assert_any_present(locators, check_visibility=True)

    def _wait_present(self, locators, timeout_warn=None, handlers=None,
                      timeout=None, check_visibility=False):
        timeout_warn = timeout_warn or self._WARN_TIMEOUT
        timeout = timeout or self._WAIT_TIMEOUT

        start_time = time.time()
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        single_loc = not _is_iterable(locators)
        locators = _to_iterable(locators)

        warned = False
        while True:
            elements = []
            for locator in locators:
                try:
                    element = locator()
                except self._not_found_exceptions as e:
                    _logger.debug(
                        'Wait ALL present. The locator (%s) did not resolve to '
                        'an element.', locator)
                    element = None
                if not element: break # None or empty sequence

                if check_visibility and not self._is_displayed(element): break
                elements.append(element)

            if len(elements) == len(locators):
                return elements[0] if single_loc else elements

            if not warned and time.time() > timeout_warn:
                self._log_screenshot(
                    'Wait ALL elements to be present. locators = %s, '
                    'check_visibility = [%s], time elapsed = [%s]s.',
                    locators, check_visibility, time.time() - start_time,
                    level=logging.WARN)
                warned = True
            handlers = self._consult_handlers(handlers)

            time.sleep(self._WAIT_INTERVAL)
            if time.time() > timeout:
                raise TimeoutError(
                    'Wait ALL elements to be present. locators = %s, '
                    'check_visibility = [%s], time elapsed = [%s]s.' %
                    (locators, check_visibility, time.time() - start_time))

    def _wait_visible(self, locators, timeout_warn=None, handlers=None, timeout=None):
        return self._wait_present(locators, timeout_warn, handlers, timeout, check_visibility=True)

    def _wait_any_present(self, locators, timeout_warn=None, handlers=None,
                          timeout=None, check_visibility=False):
        timeout_warn = timeout_warn or self._WARN_TIMEOUT
        timeout = timeout or self._WAIT_TIMEOUT

        start_time = time.time()
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        locators = _to_iterable(locators)

        warned = False
        while True:
            for locator in locators:
                try:
                    element = locator()
                except self._not_found_exceptions as e:
                    _logger.debug(
                        'Wait ANY present. The locator (%s) did not resolve to '
                        'an element.', locator)
                    element = None
                if not element: continue # None or empty sequence

                if check_visibility and not self._is_displayed(element): continue
                return element

            if not warned and time.time() > timeout_warn:
                self._log_screenshot(
                    'Wait ANY present. locators = %s, time elapsed = [%s]s.',
                    locators, time.time() - start_time, level=logging.WARN)
                warned = True
            handlers = self._consult_handlers(handlers)

            time.sleep(self._WAIT_INTERVAL)
            if time.time() > timeout:
                raise TimeoutError(
                    'Wait ANY elements to be present. locators = %s, '
                    'check_visibility = [%s], time elapsed = [%s]s.' %
                    (locators, check_visibility, time.time() - start_time))

    def _wait_any_visible(self, locators, timeout_warn=None, handlers=None,
                          timeout=None):
        return self._wait_any_present(locators, timeout_warn, handlers, timeout, check_visibility=True)

    def _wait_absent(self, locators, timeout_warn=None, minwait=3,
                     handlers=None, timeout=None, check_visibility_only=False):
        timeout_warn = timeout_warn or self._WARN_TIMEOUT
        timeout = timeout or self._WAIT_TIMEOUT

        start_time = time.time()
        timeout_appear = start_time + minwait
        timeout_warn = start_time + timeout_warn
        timeout = start_time + timeout
        locators = _to_iterable(locators)

        warned = False
        while True:
            # to avoid the situation that elements are absent simply because
            # other elements such as error dialogs are displayed.
            handlers = self._consult_handlers(handlers)
            any_invalid = False
            for locator in locators:
                try:
                    element = locator()
                except self._not_found_exceptions as e:
                    _logger.debug(
                        'Wait ALL absent. The locator (%s) did not resolve to '
                        'an element.', locator)
                    element = None
                if not element: continue

                if not check_visibility_only or self._is_displayed(element):
                    any_invalid = True
                    break

            # wait for at least 'minwait' seconds to make sure target
            # element(s) won't appear at this time.
            if not any_invalid and time.time() > timeout_appear: return
            if not warned and time.time() > timeout_warn:
                self._log_screenshot(
                    'Wait ALL elements to be absent. locators = %s, '
                    'check_visibility_only = [%s], time elapsed = [%s]s.',
                    locators, check_visibility_only, time.time() - start_time, 
                    level=logging.WARN)
                warned = True

            time.sleep(self._WAIT_INTERVAL)
            if time.time() > timeout:
                raise TimeoutError(
                    'Wait ALL elements to be absent. locators = %s, '
                    'check_visibility_only = [%s], time elapsed = [%s]s.' %
                    (locators, check_visibility_only, time.time() - start_time))

    def _wait_invisible(self, locators, timeout_warn=None, minwait=3,
                        handlers=None, timeout=None):
        self._wait_absent(locators, timeout_warn, minwait, handlers, timeout, check_visibility_only=True)

    def _watch(self, handlers, max_duration=5):
        timeout = time.time() + max_duration
        while True:
            handlers = self._consult_handlers(handlers)
            if not handlers: break
            if time.time() > timeout: break

    def _consult_handlers(self, handlers):
        if not handlers: return

        # convert handlers to a mutable list of (locator, handler)
        if isinstance(handlers, dict):
            handlers = handlers.items()
        handlers = list(handlers)
        _logger.debug('Consult handlers. handlers = %s.', [h[0] for h in handlers])

        # consult a handler at a time (rotation)
        locator, handler = handlers[0]

        try:
            element = locator()
        except self._not_found_exceptions as e:
            _logger.debug('The locator (%s) did not resolve to an element.', locator)
            element = None

        # consult the handler again later, or drop it.
        del handlers[0]
        if not element or not self._is_displayed(element) or handler(element):
            handlers.append((locator, handler))

        _logger.debug('Rotated/modified handlers: %s', [h[0] for h in handlers])
        return handlers

