class ModelNotAllowedException(Exception):
    def __init__(self, message: str):
        if not message:
            self.message = "You are not allowed to interrogate this message"
        else:
            self.message = message

class InvalidAnnotationError(Exception):
    pass
