from pyuia import AppContext

__all__ = ['SeleniumContext']

class SeleniumContext(AppContext):

    def __init__(self, driver):
        self.driver = driver
        platform = driver.desired_capabilities['platformName']
        AppContext.__init__(self, platform)

    def dump_page_source(self):
        return (self.driver.page_source, 'html')

    def take_screenshot_as_png(self):
        return self.driver.get_screenshot_as_png()

    def get_new_logs(self):
        raise NotImplementedError()

    def get_initial_logs(self):
        return self.get_new_logs()

    def quit(self):
        self.driver.quit()

