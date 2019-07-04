from setuptools import setup, Extension

with open("README.md") as fh:
    long_description = fh.read()

ext = Extension('pyquota', sources=['pyquota.c'])

setup(name='PyQuota',
      version='0.0.3',
      description='A simple python wrapper for C apis of quotactl',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='tjumyk',
      author_email='tjumyk@gmail.com',
      url='https://github.com/tjumyk/pyquota',
      ext_modules=[ext],
      classifiers=[
          'Development Status :: 3 - Alpha',
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: POSIX :: Linux",
      ])
