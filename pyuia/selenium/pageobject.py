import logging
from pyuia import PageObject, cacheable
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

__all__ = ['SeleniumPageObject', 'find_by', 'cacheable']
_logger = logging.getLogger(__name__)

class SeleniumPageObject(PageObject):

    def __init__(self, context):
        PageObject.__init__(
            self, context,
            (NoSuchElementException, StaleElementReferenceException))

    @property
    def _driver(self):
        return self._context.driver

    def _is_displayed(self, element):
        try:
            return element.is_displayed()
        except StaleElementReferenceException:
            return False

_strategy_kwargs = ['id_', 'xpath', 'link_text', 'partial_link_text',
                    'name', 'tag_name', 'class_name', 'css_selector']

from pyuia import cacheable as cacheable_decorator # naming conflict between global and parameter names

def find_by(how=None, using=None, multiple=False, cacheable=True, if_exists=False,
            context=None, scrollable=False, scroll_forward=True, scroll_vertically=True,
            scroll_margin=None, maximum_scrolls=5, driver_attr='_driver', **kwargs):
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
        scroll_margin: No-touch zone. Defaults to `None`.
        maximum_scrolls: The maximum number of attempts to scroll. Defaults to 5.
        driver_attr: The attribute name for getting the reference to WebDriver. Defaults to '_driver'.

    Kwargs:
        The following keyword arguments are supported for various locator strategies: id_ (to avoid conflict with the built-in keyword id), name, class_name, css_selector, tag_name, xpath, link_text, and partial_link_text.

    Returns: A callable which can be evaluated lazily to find UI elements.

    """
    def func(page_object):
        driver = getattr(page_object, driver_attr)

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

        # 'how' AND 'using' take precedence over keyword arguments
        if how and using:
            lookup = ctx.find_elements if multiple else ctx.find_element
            return lookup(how, using)

        if len(kwargs) != 1 or kwargs.keys()[0] not in _strategy_kwargs :
            raise ValueError(
                "If 'how' AND 'using' are not specified, one and only one of the following "
                "valid keyword arguments should be provided: %s." % _strategy_kwargs)

        key = kwargs.keys()[0]; value = kwargs[key]
        suffix = key[:-1] if key.endswith('_') else key # find_element(s)_by_xxx
        prefix = 'find_elements_by' if multiple else 'find_element_by'
        lookup = getattr(ctx, '%s_%s' % (prefix, suffix))

        scrolls = 0;
        while True:
            try:
                return lookup(value)
            except NoSuchElementException:
                if not scrollable or scrolls == maximum_scrolls:
                    if if_exists: return None
                    raise

                scroller = _get_scroller(page_object, container, scrollable)
                _scroll(page_object, driver, scroller, scroll_forward, scroll_vertically, scroll_margin)
                scrolls += 1

    return cacheable_decorator(func, cache_none=not if_exists) if cacheable else func

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

def _scroll(page_object, driver, scroller, forward, vertically, margin):
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
    if isinstance(margin, (int, float)):
        if isinstance(margin, float):
            margin = int((h if vertically else w) * margin)

        offset = margin if forward else -margin

        if vertically:
            y1 += offset
        else:
            x1 += offset
    elif margin is not None:
        margin = margin(page_object) if callable(margin) else margin
        if margin is not None:
            loc, size = margin.location, margin.size
            x, y, w, h = loc['x'], loc['y'], size['width'], size['height']

            if vertically:
                y1 = y - 1 if forward else y + h + 1
            else:
                x1 = x - 1 if forward else x + w + 1

    driver.swipe(x1, y1, x2, y2, 2000)

