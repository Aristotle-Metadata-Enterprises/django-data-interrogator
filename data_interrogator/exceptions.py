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

class DuplicateAnnotationCommand(Exception):
    def __init__(self, aggregate, other_aggregate):
        self.message = (
            f'DuplicateAnnotationCommand - The registered aggregate {aggregate} uses a duplicate command {aggregate.command}. '
            f'This is already defined for {other_aggregate}'
        )
