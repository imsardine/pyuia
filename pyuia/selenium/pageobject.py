import sys, logging
from pyuia import PageObject, cacheable
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By

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
            displayed = element.is_displayed()
            _logger.debug('Element (%s) is displayed? %s.', element.id, displayed)
            return displayed
        except StaleElementReferenceException:
            logging.debug('Element (%s) is NOT displayed because of stale reference.', element.id)
            return False

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
            context=None, driver_attr='_driver', **kwargs):
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
        context: The starting point of a search.
        driver_attr: The attribute name for getting the reference to WebDriver. Defaults to '_driver'.

    Kwargs:
        The following keyword arguments are supported for various locator strategies: id_ (to avoid conflict with the built-in keyword id), name, class_name, css_selector, tag_name, xpath, link_text, and partial_link_text.

    Returns: A callable which can be evaluated lazily to find UI elements.

    """
    # 'how' AND 'using' take precedence over keyword arguments
    _how, _using = how, using
    if not (_how and _using):
        if len(kwargs) != 1 or kwargs.keys()[0] not in _strategy_kwargs.keys() :
            raise ValueError(
                "If 'how' AND 'using' are not specified, one and only one of the following "
                "valid keyword arguments should be provided: %s." % _strategy_kwargs.keys())

        key = kwargs.keys()[0]
        _how, _using = _strategy_kwargs[key], kwargs[key]

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

        lookup = ctx.find_elements if multiple else ctx.find_element

        try:
            return lookup(_how, _using)
        except NoSuchElementException as e:
            if if_exists: return None
            msg = "%s ; find_by(how='%s', using='%s', multiple=%s, cacheable=%s, " \
                  "if_exists=%s, context=%s)" % \
                  (str(e), _how, repr(_using), multiple, cacheable, if_exists, context)
            raise NoSuchElementException(msg), None, sys.exc_info()[2]

    func = cacheable_decorator(func, cache_none=not if_exists) if cacheable else func

    # for debugging, expose criteria of the lookup
    func.__name__ = "find_by(how='%s', using=%s, multiple=%s, cacheable=%s, " \
                    "if_exists=%s, context=%s)" % \
                    (_how, repr(_using), multiple, cacheable, if_exists, context)
    return func

