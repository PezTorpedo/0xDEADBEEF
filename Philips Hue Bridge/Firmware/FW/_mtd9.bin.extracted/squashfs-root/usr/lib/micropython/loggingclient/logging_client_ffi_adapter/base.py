class LoggingClientFFIAdapterBase:
    @property
    def FFI_NULL(self):
        raise NotImplementedError()

    def createDiagnosticsClientInterface(self, address, component):
        raise NotImplementedError()
    
    def logDiagnostics(self, ffi_diagnostics_client_interface, category, type_, sub_type, event_data):
        raise NotImplementedError()
    
    def delete(self, ffi_diagnostics_client_interface):
        raise NotImplementedError()