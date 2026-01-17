from .logging_client_ffi_adapter.factory import LoggingClientFFIAdapterFactory
from .errors import InitialisationError, LoggingError


logging_client_ffi_adapter = LoggingClientFFIAdapterFactory.create()


class LoggingClient:
    def __init__(self, component: str, address: str = '', port: int = -1):
        self._ffi_logging_client_interface = logging_client_ffi_adapter.create_diagnostics_client_interface(address, component, port)
        if self._ffi_logging_client_interface == logging_client_ffi_adapter.FFI_NULL:
            raise InitialisationError()
    
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def log(self, category, type_, sub_type, event_data):
        ret = logging_client_ffi_adapter.log_diagnostics(self._ffi_logging_client_interface, category, type_, sub_type, event_data)
        if ret != 0:
            raise LoggingError()
    
    def close(self):
        logging_client_ffi_adapter.delete(self._ffi_logging_client_interface)