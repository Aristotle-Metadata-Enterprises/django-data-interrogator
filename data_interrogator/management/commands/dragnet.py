from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models.fields.related import ForeignKey
from parlhand import models
import csv
import time
from parlhand.management.commands import utils as import_utils
import reversion
from optparse import make_option

class Command(BaseCommand):
    args = 'csv_file_name'
    help = 'Uploads a generic CSV'

    option_list = BaseCommand.option_list + (
        make_option('-D','--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='Turn on debug'),
        make_option('-s','--separator',
            action='store',
            dest='sep',
            default=',',
            help='Define column separator (default: ,)'),
        make_option('-m','--model',
            action='store',
            dest='model_name',
            default=None,
            help='Define model to insert into (default: uses filename)'),
        make_option('-l','--lines',
            action='store',
            dest='line_nos',
            default=None,
            help='Which lines to process. (default: process all lines)'),
        make_option('-F','--force',
            action='store_true',
            dest='force_create',
            default=False,
            help='Force creation instead of get_or_create. Useful when loading generics'),
        make_option('-G','--generic',
            action='store',
            dest='generic_model_name',
            default=None,
            help='Generic relation we are inserting to the chosen model'),
        make_option('-k','--update_keys',
            action='store',
            dest='update_keys',
            default=None,
            help='Comma separated list to Specify which columns are keys when searching - all other columns are updated'),
        )

    def handle(self, *args, **options):
        self.debug_mode = options['debug']
        requested_model = options['model_name']
        generic_model = options['generic_model_name']
        separator = options['sep']
        verbosity = int(options['verbosity'])
        lines = options['line_nos']
        update_keys = options['update_keys']
        generic_map = {}

        if update_keys:
            update_keys = options['update_keys'].split(',')

        if lines:
            lines = sorted(map(int,lines.split('-',1)))
            if len(lines) == 0:
                lines = [lines[0],lines[0]+1]
        elif self.debug_mode:
            lines = [0,2]
            
        if not args or len(args) == 0:
            print(self.help)
            return
        elif len(args) == 1:
            filename = args[0]
        else:
            print("Wrong number of arguments")
            return

        if requested_model is None:
            path,fn = filename.rsplit('/',1)
            requested_model,ext = fn.rsplit('.',1)

        if separator in ['\\t','tab']:
            separator = '\t'

        try:
            app_label,model = requested_model.lower().split('.',1)
            model = ContentType.objects.get(app_label=app_label,model=model).model_class()
        except ContentType.DoesNotExist:
            print("Model does not exist - %s"%requested_model)
            return 

        with open(filename, 'r') as imported_csv:
            reader = csv.reader(imported_csv,delimiter=separator)  # creates the reader object
            headers = reader.next() # get the headers

            if generic_model is not None:
                if generic_model == 'FILENAME':
                    path,fn = filename.rsplit('/',1)
                    generic_model,ext = fn.rsplit('.',1)
                    csv_field=headers[0]
                    generic_key=headers[0]
                    generic_field='content_object'
                elif len(generic_model.split(':')) == 4:
                    generic_field,csv_field,generic_model,generic_key = generic_model.split(':',3)
                elif len(generic_model.split(':')) == 3:
                    generic_field,csv_field,generic_model = generic_model.split(':',2)
                    generic_key=headers[0]
                else:
                    generic_field,generic_model = generic_model.split(':',1)
                    csv_field='content_object'
                    generic_key=headers[0]
                g_app_label,g_model = generic_model.lower().split('.',1)
                try:
                    generic_model_type = ContentType.objects.get(app_label=g_app_label,model=g_model)
                    generic_model = generic_model_type.model_class()
                    generic_map[csv_field]=(generic_field,generic_model,generic_key)
                except ContentType.DoesNotExist:
                    print("Model does not exist - %s"%generic_model)
                    return 
            print("importing file <%s> in as model <%s>"%(filename,requested_model))
            start_time = time.time()

            failed = []
            success = []
            skipped = []
            for i,row in enumerate(reader):   # iterates the rows of the file in order
                if len(failed) > 100:
                    print('something has gone terribly wrong.') 
                    break
                if lines:
                    if i < lines[0]:
                        continue
                    elif i >= lines[1]:
                        break
                    
                special_starts = (  '_', # ignored column
                                    '+', # many-to-many id field
                                    '=', # assign value to a property after saving
                                    #'*', # Generics
                                )
                if update_keys:
                    update_vals = dict(  [(clean(key),clean(val))
                                for key,val in zip(headers,row)
                                if key in update_keys])
                else:
                    update_vals = []
                    
                values = dict(  [(clean(key),clean(val))
                                for key,val in zip(headers,row)
                                if '.' not in key
                                    and not clean(key).startswith(special_starts)
                                    and not val == ''
                                    and clean(key) not in generic_map.keys()])
                rels = dict([   (clean(key),clean(val))
                                for key,val in zip(headers,row)
                                if '.' in key and not clean(key).startswith(special_starts)])
                many = dict([   (clean(key),clean(val))
                                for key,val in zip(headers,row)
                                if '.' not in key
                                    and clean(key).startswith('+')
                                    and not val == ''])
                funcs = dict([   (clean(key),clean(val))
                                for key,val in zip(headers,row)
                                if '.' not in key
                                    and clean(key).startswith('=')
                                    and not val == ''])
                generics = dict([   (clean(key),clean(val))
                                for key,val in zip(headers,row)
                                if '.' not in key
                                    and clean(key) in generic_map.keys()
                                    and not val == ''])

                try:
                    with transaction.atomic():
                        # We might be trying to make a new thing that requires a foreign key
                        # Lets construct it instead and try that....
                        fk_fields = [f for f in model._meta.fields if f.__class__ == ForeignKey]
                        models = []
                        for f in fk_fields:
                            try:
                                related_model = f.related.parent_model
                            except AttributeError:
                                related_model = f.related.model
                            models.append(related_model)
                        models = set(models)
                        rel_items = {}
                        if models:
                            for rel,val in rels.items():
                                # Let this fail if there are too few or too many
                                rel_app_label,rel_model_name,rel_field = rel.rsplit('.')
                                _rel = (rel_app_label,rel_model_name)
                                rel_items[_rel] = rel_items.get(_rel,[]) + [(rel_field,val)]
                        for _app,fields in rel_items.items():
                            app,sub_model_name = _app
                            if '|' in app:
                                field_name,app = app.split('|')
                            else:
                                field_name = sub_model_name
                            sub_model = ContentType.objects.get(app_label=app,model=sub_model_name).model_class()
                            rel_obj,c = sub_model.objects.get_or_create(**dict(fields))
                            if c and verbosity >=2:
                                print('created sub item - %s - %s'%(sub_model,rel_obj))
                                if verbosity >= 3:
                                    print('   from %s'%dict(fields))
                            values[field_name] = rel_obj
                        if self.debug_mode:
                            print(values)

                        if generics:
                            for field,val in generics.items():
                                field = field.strip('*')
                                generic_field,g_model,lookup_key = generic_map[field]
                                funcs[generic_field] = g_model(**{lookup_key:val})
                        if options['force_create']:
                            obj = model(**values)
                            created = True
                        else:
                            if update_vals:
                                obj,created = model.objects.update_or_create(defaults=values,**update_vals)
                                print('updated',obj)
                            else:
                                obj,created = model.objects.get_or_create(**values)
                        for field_name,val in many.items():
                            field = getattr(model,field_name.strip('+'))
                            manager = getattr(obj,field_name.strip('+'))
                            vals=[s.strip() for s in val.split('|') if s.strip() != '']
                            for v in vals:
                                p = field.field.related_model.objects.get(pk=v)
                                manager.add(p)
                        if options['force_create']:
                            created = True
                        if created:
                            success.append(i)
                            for f,val in funcs.items():
                                f = f.lstrip('=')
                                setattr(obj,f,val)
                            obj.save()
                        else:
                            if verbosity>=2:
                                print("Line %s - skipped"%i)
                                print(verbosity)
                            if verbosity==3:
                                print(row)
                            skipped.append(i)
                    # end transaction
                except Exception as e:
                    if verbosity >=2:
                        print("Line %s - %s"%(i,e))
                    if self.debug_mode:
                        raise
                    failed.append(i)
        elapsed_time = time.time() - start_time
        print("Summary:")
        if verbosity >=1:
            print("  Time taken: %.3f seconds"%elapsed_time)
        print("  Success: %s"%len(success))
        if skipped:
            print("  Skipped: %s"%len(skipped))
        if failed:
            print("  Failed: %s"%len(failed))
            print("  Failed on lines: %s"%str(failed))

def clean(string):
    return string.strip('"').strip().replace("\"","")
