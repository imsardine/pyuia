import time
from ..selenium import SeleniumPageObject, cacheable
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By

__all__ = ['AppiumPageObject', 'find_by', 'cacheable']

class AppiumPageObject(SeleniumPageObject):

    def _press_menu(self):
        self._driver.keyevent(82)
        time.sleep(1) # or then menu may not in the subsequent screenshot.

    def _press_back(self):
        self._driver.keyevent(4)

_strategy_kwargs = {
    'id_': By.ID,
    'xpath': By.XPATH,
    'link_text': By.LINK_TEXT,
    'partial_link_text': By.PARTIAL_LINK_TEXT,
    'name': By.NAME,
    'tag_name': By.TAG_NAME,
    'class_name': By.CLASS_NAME,
    'css_selector': By.CSS_SELECTOR }

from pyuia import cacheable as cacheable_decorator # naming conflict between global and parameter names

def find_by(how=None, using=None, multiple=False, cacheable=True, if_exists=False,
            context=None, scrollable=False, scroll_forward=True, scroll_vertically=True,
            scroll_starting_padding=None, scroll_ending_padding=None, maximum_scrolls=5, driver_attr='_driver', **kwargs):
    """Create a callable which can be evaluated lazily to find UI elements.

    This function implements the concept mentioned in Page Factory (or PageFactory) pattern (https://code.google.com/p/selenium/wiki/PageFactory). It helps to reduce the amount of boilerplate code while implementing page objects. For more details, see https://jeremykao.wordpress.com/2015/06/10/pagefactory-pattern-in-python/.

    Args:
        how: Locator strategy. It can be one of the class variables defined in
            `selenium.webdriver.common.by.By`, e.g., `By.ID`, `By.NAME` etc.
        using: The locator.
        multiple: Whether the lookup return multiple elements.
        cacheable: Whether to cache the result.
        if_exists: Whether to return `None` to indicate the element doesn't exist,
            instead of raising an exception.
        context: The starting point of a search, and the scrollable container
            if argument `scrollable` is set to `True` explicitly.
        scrollable: Whether to perform scroll actions if the element is not found.
            Defaults to `False`.
        scroll_forward: Whether to scroll forward or backward. Defaults to `True`.
        scroll_vertically: Whether to scroll vertically or horizontally. Defaults to `True`.
        scroll_starting_padding: No-touch starting zone. Defaults to `None`.
        scroll_ending_padding: No-touch ending zone. Defaults to `None`.
        maximum_scrolls: The maximum number of attempts to scroll. Defaults to 5.
        driver_attr: The attribute name for getting the reference to WebDriver. Defaults to '_driver'.

    Kwargs:
        The following keyword arguments are supported for various locator strategies: id_ (to avoid conflict with the built-in keyword id), name, class_name, css_selector, tag_name, xpath, link_text, and partial_link_text.

    Returns: A callable which can be evaluated lazily to find UI elements.

    """
    # 'how' AND 'using' take precedence over keyword arguments

    # If _how == 'name', we will replace it by 'xpath' in func.
    # However, since variable cannot be updated in different scope (i.e., find_by & func here),
    # We use dictionary instead.
    method_dic = {'_how':how, '_using': using}

    if not (method_dic['_how'] and method_dic['_using']):
        if len(kwargs) != 1 or kwargs.keys()[0] not in _strategy_kwargs.keys() :
            raise ValueError(
                "If 'how' AND 'using' are not specified, one and only one of the following "
                "valid keyword arguments should be provided: %s." % _strategy_kwargs.keys())

        key = kwargs.keys()[0]
        method_dic['_how'], method_dic['_using'] = _strategy_kwargs[key], kwargs[key]

    def func(page_object):
        driver = getattr(page_object, driver_attr)

        # For appium v1.5.0+, since it doesn't support find by name strategy, we have to adjust our pyuia
        # We replace name with xpath
        # Github release note: https://github.com/appium/appium/releases/tag/v1.5.0
        # Discuss thread: https://discuss.appium.io/t/appium-1-5-fails-to-find-element-by-name/8857/10

        if method_dic['_how'] == 'name':
            method_dic['_how'] = 'xpath'
            method_dic['_using'] = "//*[@text='" + method_dic['_using'] + "' or @content-desc='" + method_dic['_using'] + "']"

        # ctx - driver or a certain element
        if context is None:
            ctx = driver
            container = None
        elif callable(context):
            container = ctx = context(page_object)
            if not ctx:
                if if_exists:
                    return None
                else:
                    raise NoSuchElementException("The element as the context doesn't exist.")
        else: # element
            container = ctx = context

        lookup = ctx.find_elements if multiple else ctx.find_element

        scrolls = 0;

        while True:
            try:
                return lookup(method_dic['_how'], method_dic['_using'])

            except NoSuchElementException as e:

                if not scrollable or scrolls == maximum_scrolls:
                    if if_exists: return None
                    msg = "%s ; find_by(how='%s', using='%s', multiple=%s, cacheable=%s, " \
                          "if_exists=%s, context=%s, scrollable=%s)" % \
                          (str(e), method_dic['_how'], method_dic['_using'], multiple, cacheable, if_exists, context, scrollable)
                    raise NoSuchElementException(msg), None, sys.exc_info()[2]

                scroller = _get_scroller(page_object, container, scrollable)
                _scroll(page_object, driver, scroller, scroll_forward,
                        scroll_vertically, scroll_starting_padding, scroll_ending_padding)
                scrolls += 1

    func = cacheable_decorator(func, cache_none=not if_exists) if cacheable else func

    # for debugging, expose criteria of the lookup
    func.__name__ = "find_by(how='%s', using=%s, multiple=%s, cacheable=%s, " \
                    "if_exists=%s, context=%s, scrollable=%s)" % \
                    (method_dic['_how'], repr(method_dic['_using']), multiple, cacheable, if_exists, context, scrollable)
    return func

def _get_scroller(page_object, container, scrollable):
    if callable(scrollable): # find_by
        scroller = scrollable(page_object)
        if not scroller:
            raise ValueError("The element as the scrollable container doesn't exist.")
        return scroller
    elif scrollable is True:
        if container is None:
            raise ValueError("The argument 'context' is mandatory if argument 'scrollable' is set to True explicitly.")
        else:
            return container
    else: # element
        return scrollable

def _scroll(page_object, driver, scroller, forward, vertically, starting_padding, ending_padding):
    loc, size = scroller.location, scroller.size
    x, y, w, h = loc['x'], loc['y'], size['width'], size['height']

    if vertically:
        points = [(x + w / 2, y + h - 1), (x + w / 2, y + 1)]
    else:
        points = [(x + w - 1, y + h / 2), (x + 1, y + h / 2)]

    if not forward:
        points.reverse()

    x1, y1 = points[0]
    x2, y2 = points[1]

    # take margin (no-touch zone) into account
    if isinstance(starting_padding, (int, float)):
        if isinstance(starting_padding, float):
            starting_padding = int((h if vertically else w) * starting_padding)

        offset = -starting_padding if forward else starting_padding

        if vertically:
            y1 += offset
        else:
            x1 += offset
    elif starting_padding is not None:
        starting_padding = starting_padding(page_object) if callable(starting_padding) else starting_padding
        if starting_padding is not None:
            loc, size = starting_padding.location, starting_padding.size
            x, y, w, h = loc['x'], loc['y'], size['width'], size['height']

            if vertically:
                y1 = y - 1 if forward else y + h + 1
            else:
                x1 = x - 1 if forward else x + w + 1

    if isinstance(ending_padding, (int, float)):
        if isinstance(ending_padding, float):
            ending_padding = int((h if vertically else w) * ending_padding)

        offset = ending_padding if forward else -ending_padding

        if vertically:
            y2 += offset
        else:
            x2 += offset
    elif ending_padding is not None:
        ending_padding = ending_padding(page_object) if callable(ending_padding) else ending_padding
        if ending_padding is not None:
            loc, size = ending_padding.location, ending_padding.size
            x, y, w, h = loc['x'], loc['y'], size['width'], size['height']

            if vertically:
                y2 = y + h + 1 if forward else y - 1
            else:
                x2 = x + w + 1 if forward else x - 1
    driver.swipe(x1, y1, x2, y2, abs(x1-x2+y1-y2)*3)
