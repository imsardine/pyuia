import logging
from pyuia import PageObject
from selenium.common.exceptions import NoSuchElementException

__all__ = ['SeleniumPageObject']
_logger = logging.getLogger(__name__)

class SeleniumPageObject(PageObject):

    def __init__(self, context):
        PageObject.__init__(self, context, NoSuchElementException)

    @property
    def _driver(self):
        return self._context.driver

    def _is_displayed(self, element):
        return element.is_displayed()

