PyUIA
=====

PyUIA stands for Python UI Automation. It is a library/framework aiming to facilitate the implementation of UI test automation on various platforms, including mobile and desktop OSs.

UI test automation is brittle to (inevitable) changes in UI. PyUIA emphasizes [keyword-driven testing approach](http://en.wikipedia.org/wiki/Keyword-driven_testing) and [Page Object Pattern](http://martinfowler.com/bliki/PageObject.html), and that results in test code organized in a more manageable way that scales.

The diagram below indicates where PyUIA fits into.

```
.------------------------.
|      Requirements      |
|------------------------|
|        Keywords        |
'------------------------'
                           ---.
.------------------------.    |
|      Keyword Impl.     |    |
'----------/---\---------'    |
         /       \            |
.-------v---. .---v------.     > Where PyUIA fits into
| Page Obj. | | Page Obj.|    |
| (Android) | |  (iOS)   |    |
'-----------' '----------'    |
                           ---' 
.------------------------.
|      Testing Tools     |
|------------------------|
| Application Under Test |
'------------------------'
```

For a real example about how PyUIA works with WordPress for Android, refer to [imsardine/pyuia-example-wordpress](https://github.com/imsardine/pyuia-example-wordpress). Here is the [testing result](https://cdn.rawgit.com/imsardine/pyuia-example-wordpress/master/output/log.html) worth looking at. Do not miss embedded screenshots and SEPERATED device logs collected during each keyword execution.

Installation
------------

If you have Python with Pip or EasyInstall installed, simply run:

```shell
pip install pyuia
```

or

```shell
easy_install install pyuia
```

Alternatively, if you perfer to install it from source, just clone the repository and run:

```shell
python setup install
```

Robot Framework Keyword Implementation
--------------------------------------

 * `pyuia.robot.BaseAppLibrary` - A base class for creating AN _Application Library_ for your app.
 * `pyuia.robot.BasePageLibrary` - A base class for creating _Page/Screen Libraries_ for each page/screen (object) you are going to model.

Page Object Implementation
--------------------------

 * `pyuia.PageObject` - A generic (technology-independent) implementation of Page Object Pattern. It provides several utility methods for asserting/waiting the presence/absence of UI elements.
 * `pyuia.selenium.SeleniumPageObject` - A base class for creating page objects that drive Selenium internally.
 * `pyuia.appium.AppiumPageObject` -  A base class for creating page objects that drive Appium internally.

License
-------

MIT
