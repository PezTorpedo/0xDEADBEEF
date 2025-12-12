class LoggingClientError(Exception):
    message: str

    def __init__(self):
        super().__init__(self.message)

class InitialisationError(LoggingClientError):
    message = "Failed to initialize diagnostics-client library interface"

class LoggingError(LoggingClientError):
    message = "Failed to send log through diagnostics-client library"