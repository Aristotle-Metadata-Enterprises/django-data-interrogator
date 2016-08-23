def get_suspect(app_label,model):
    from django.contrib.contenttypes.models import ContentType
    
    return ContentType.objects.get(app_label=app_label.lower(),model=model.lower()).model_class()

def normalise_field(text):
    return text.strip().replace('(','::').replace(')','').replace(".","__")

def clean_filter(text):
    maps = [('<=','lte'),('<','lt'),('>=','gte'),('>','gt'),('<>','ne'),('=','')]
    for a,b in maps:
        candidate = text.split(a)
        if len(candidate) == 2:
            if a is "=":
                return candidate[0], b, candidate[1]
            return candidate[0], '__%s'%b, candidate[1]
    return text
