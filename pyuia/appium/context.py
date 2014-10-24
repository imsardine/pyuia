from ..selenium import SeleniumContext
from .util import get_logs

__all__ = ['AppiumContext']

class AppiumContext(SeleniumContext):

    def dump_page_source(self):
        return (self.driver.page_source, 'xml')

    def get_new_logs(self):
        log_type = 'syslog' if self.platform == 'iOS' else 'logcat'
        return get_logs(self.driver, log_type)

