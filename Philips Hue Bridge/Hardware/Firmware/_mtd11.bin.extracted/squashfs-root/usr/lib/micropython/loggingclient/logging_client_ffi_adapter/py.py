from cffi import FFI

from .base import LoggingClientFFIAdapterBase


class LoggingClientFFIAdapterPy(LoggingClientFFIAdapterBase):
    @property
    def FFI_NULL(self):
        return self.ffi.NULL

    def __init__(self):
        self.ffi = FFI()
        self.ffi.cdef("void* createDiagnosticsClient(char* address, char* component, int port);")
        self.ffi.cdef("int logDiagnostics(void* client, char* category, char* type, char* sub_type, char* body);")
        self.ffi.cdef("void deleteDiagnosticsClient(void* client);")
        # PIN API version rationale (this also applies to MicroPython wrapper):
        #   - A mismatch between the current library version and pinned version would be highlighed as a failure in tests, because the CI starts from a clean build, so no more harm than re-runing the pipeline (when version number is bumped) will be caused.
        #   - It several library versions were to be allowed in the bridge, this pinning ensures each wrapper version uses the right library version.
        self._lib = self.ffi.dlopen("libloggingclient.so.2")

    def _args_to_cffi(self, *args):
        return [arg.encode() if isinstance(arg, str) else arg for arg in args]

    def create_diagnostics_client_interface(self, address, component, port: int = -1):
        return self._lib.createDiagnosticsClient(*self._args_to_cffi(address, component, port))
    
    def log_diagnostics(self, ffi_diagnostics_client_interface, category, type_, sub_type, event_data):
        return self._lib.logDiagnostics(ffi_diagnostics_client_interface, *self._args_to_cffi(category, type_, sub_type, event_data))
    
    def delete(self, ffi_diagnostics_client_interface):
        self._lib.deleteDiagnosticsClient(ffi_diagnostics_client_interface)