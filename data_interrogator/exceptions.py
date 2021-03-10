class ModelNotAllowedException(Exception):
    def __init__(self, model=None):
        if not model:
            self.message = \
                "ModelNotAllowedException - Please double check that you are allowed to interrogate all models"
        else:
            self.message = f'ModelNotAllowedException - You are not allowed to interrogate {model}'

    def __str__(self):
        return f'{self.message}'


class InvalidAnnotationError(Exception):
    pass
