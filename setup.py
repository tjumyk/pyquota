from setuptools import setup, Extension

setup(
    packages=["pyquota"],
    ext_modules=[Extension("pyquota._native", sources=["pyquota.c"])],
)
