# stolen from:
# http://stackoverflow.com/questions/21925671/convert-django-model-object-to-dict-with-all-of-the-fields-intact
from django.db.models.fields.related import ManyToManyField


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                data[f.name] = list(
                    f.value_from_object(instance).values_list("pk", flat=True)
                )
        else:
            data[f.name] = f.value_from_object(instance)
    return data


# very clever! stolen from:
# http://stackoverflow.com/questions/7499767/temporarily-disable-auto-now-auto-now-add


def do_field(Clazz, field_name, func):
    func(Clazz._meta.get_field(field_name))


def turn_off_auto_now(Clazz, field_name):
    def auto_now_off(field):
        field.auto_now = False

    do_field(Clazz, field_name, auto_now_off)


def turn_off_auto_now_add(Clazz, field_name):
    def auto_now_add_off(field):
        field.auto_now_add = False

    do_field(Clazz, field_name, auto_now_add_off)
