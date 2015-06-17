from setuptools import setup

setup(
  name = 'pyuia',
  license = 'MIT',
  packages = [
      'pyuia',
      'pyuia.robot',
      'pyuia.selenium',
      'pyuia.appium',
  ],
  version = '0.3.0',
  description = 'PyUIA is a library aiming to facilitate the implementation of UI test automation with Python.',
  author = 'KKBOX SQA Team',
  author_email = 'imsardine@gmail.com',
  url = 'https://github.com/imsardine/pyuia',
  keywords = [
      'python',
      'ui test automation',
      'keyword-driven testing',
      'page object pattern',
      'appium',
      'robot framework',
      'mobile', 'android', 'ios',
  ],
  classifiers = [
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
      'Topic :: Software Development :: Quality Assurance',
      'Topic :: Software Development :: Testing',
  ],
  install_requires = ['selenium', 'Appium-Python-Client'],
)
