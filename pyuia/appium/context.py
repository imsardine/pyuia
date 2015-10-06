from ..selenium import SeleniumContext
from .util import get_logs

__all__ = ['AppiumContext']

class AppiumContext(SeleniumContext):

    def dump_page_source(self):
        return (self.driver.page_source, 'xml')

    def get_new_logs(self):
        log_type = 'syslog' if self.platform == 'iOS' else 'logcat'
        return get_logs(self.driver, log_type)

    def open_app(self, reset):
        if reset:
            # "remove -> launch" is more efficient than "launch -> reset"
            self._remove_app()
            self.driver.launch_app()
        else:
            self.driver.launch_app()

    def _remove_app(self):
        caps = self.driver.capabilities
        platform = caps['platformName']
        if platform == 'Android':
            self.driver.remove_app(caps['appPackage'])
        elif platform == 'iOS':
            self.driver.remove_app(caps['bundleId'])
        else:
            assert False, platform

    def close_app(self):
        self.driver.close_app()

