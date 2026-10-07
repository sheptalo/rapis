from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension("rapis._speedups", ["rapis/_speedups.c"], optional=True)
    ]
)
