def get_base_model(app_label, model):
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label=app_label.lower(), model=model.lower()).model_class()


def normalise_field(text):
    return text.strip().replace('(', '::').replace(')', '').replace(".", "__")


