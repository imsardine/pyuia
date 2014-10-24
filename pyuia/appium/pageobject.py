import time
from ..selenium import SeleniumPageObject

__all__ = ['AppiumPageObject']

class AppiumPageObject(SeleniumPageObject):

    def _press_menu(self):
        self._driver.keyevent(82)
        time.sleep(1) # or then menu may not in the subsequent screenshot.

    def _press_back(self):
        self._driver.keyevent(4)

