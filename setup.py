from distutils.core import setup, Extension

ext = Extension('pyquota', sources=['pyquota.c'])

setup(name='PyQuota',
      version='1.0.0',
      description='This is the first version',
      author='tjumyk',
      author_email='tjumyk@gmail.com',
      url='https://github.com/tjumyk/pyquota',
      ext_modules=[ext])
