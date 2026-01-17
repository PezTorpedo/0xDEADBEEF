import sys


class LoggingClientFFIAdapterFactory:
    @staticmethod
    def create():
        if sys.implementation.name == 'micropython':
            from .mpy import LoggingClientFFIAdapterMPy
            return LoggingClientFFIAdapterMPy()
        elif sys.implementation.name == 'cpython':
            from .py import LoggingClientFFIAdapterPy
            return LoggingClientFFIAdapterPy()
        else:
            raise NotImplementedError()