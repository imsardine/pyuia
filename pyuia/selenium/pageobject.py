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
            context=None, driver_attr='_driver', max_swipe_times=5, **kwargs):


    def func(self):

        def swipe_up(times=1):
            """Swipe up from [500, 1800] to [500, 400] within 1 sec. 
                Default swipe times is 1."""
            for i in range(times):
                ctx.swipe(500, 1800, 500, 400, 1000)


        def swipe_down(times=1):
            """Swipe down from [500, 400] to [500, 1800] within 1 sec. 
                Default swipe times is 1."""
            for i in range(times):
                ctx.swipe(500, 400, 500, 1800, 1000)


        # context - driver or a certain element
        if callable(context):
            ctx = context(self)
            if not ctx:
                if if_exists:
                    return None
                else:
                    raise NoSuchElementException("The element as the context doesn't exist.")
        else:
            ctx = getattr(self, driver_attr)

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


        current_time = 0
        while True:
            try:
                return lookup(value)
            except NoSuchElementException:
                if if_exists: return None
                if current_time ==0:
                    swipe_down(max_swipe_times)
                else:
                    if current_time > max_swipe_times: raise
                    swipe_up()
                    
                current_time+=1

    return cacheable_decorator(func, cache_none=not if_exists) if cacheable else func