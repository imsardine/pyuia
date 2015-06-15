import logging
from pyuia import PageObject, cacheable
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

__all__ = ['SeleniumPageObject', 'find_by', 'cacheable']
_logger = logging.getLogger(__name__)

class SeleniumPageObject(PageObject):

    def __init__(self, context):
        PageObject.__init__(self, context, NoSuchElementException)

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

def find_by(how=None, using=None, multiple=False, cacheable=True, context=None, driver_attr='_driver', **kwargs):
    def func(self):
        # context - driver or a certain element
        ctx = context(self) if callable(context) else getattr(self, driver_attr)

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
        return lookup(value)

    return cacheable_decorator(func) if cacheable else func

