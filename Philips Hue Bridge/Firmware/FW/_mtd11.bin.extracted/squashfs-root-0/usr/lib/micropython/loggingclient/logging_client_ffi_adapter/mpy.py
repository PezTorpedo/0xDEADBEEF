import ffi

from .base import LoggingClientFFIAdapterBase


class LoggingClientFFIAdapterMPy(LoggingClientFFIAdapterBase):
    @property
    def FFI_NULL(self):
        return 0

    def __init__(self):
        self._lib = ffi.open("libloggingclient.so.2")    # About the version, see comment in Python FFI Adapter
        self.create_diagnostics_client_interface_ = self._lib.func('p', 'createDiagnosticsClient', 'ssi')
        self.log_diagnostics_ = self._lib.func('i', 'logDiagnostics', 'pssss')
        self.delete_ = self._lib.func('v', 'deleteDiagnosticsClient', 'p')

    def create_diagnostics_client_interface(self, address, component, port: int = -1):
        return self.create_diagnostics_client_interface_(address, component, port)
    
    def log_diagnostics(self, ffi_diagnostics_client_interface, category, type_, sub_type, event_data):
        return self.log_diagnostics_(ffi_diagnostics_client_interface, category, type_, sub_type, event_data)
    
    def delete(self, ffi_diagnostics_client_interface):
        self.delete_(ffi_diagnostics_client_interface)