'''
A custom serializer that extends the Django REST Framework's base serializer. It allows
the API endpoint to have dynamic fields. In essence, the serializer stores a reference
to an instance of the 'Form' model, which has a one-to-many relation to the 'Field' model.
The dynamic API endpoint's fields are created as per the fields on the Form instance.

This was a specific project requirement. The front-end is a Vue.js SPA which runs off an API.
The project required dynamic forms on the front-end, hence the API endpoint to receive the 
data. In production, this endpoint is used in pair with another one, which exposes 
"form template fields" so that the front-end knows what form fields to render to users and 
what data to submit.
'''

from collections import OrderedDict
from consultmed.models.exceptions import TemplateMetaSyntaxVersionError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework import fields as drf_fields
from consultmed.choices import FieldTypes
from consultmed.models import Form, FormTemplate, FieldDefinition
from api_v1.serializers import utils


###########
# HELPERS #
###########
def get_latest_form_representator_class():
    return FormRepresentatorV11


def get_form_representator_class_for(template: FormTemplate):
    if template.tmsv == template.TMSV.V10:
        return FormRepresentatorV10
    elif template.tmsv == template.TMSV.V11:
        return FormRepresentatorV11
    else:
        raise TemplateMetaSyntaxVersionError(
            'FormRepresentation for TMS version `%s` does not exist' %
            template.tmsv
        )


def get_form_representator_for(form: Form):
    representator_class = get_form_representator_class_for(form.template)
    return representator_class(form)


def get_latest_form_serialiser_class():
    return FormSerializerV11


def get_form_serializer_class_for(template: FormTemplate):
    if template.tmsv == template.TMSV.V10:
        return FormSerializerV10
    elif template.tmsv == template.TMSV.V11:
        return FormSerializerV11
    else:
        raise TemplateMetaSyntaxVersionError(
            'FormSerializer for TMS version `%s` does not exist' %
            template.tmsv
        )


def get_form_serializer_for(form: Form):
    serializer_class = get_form_serializer_class_for(form.template)
    return serializer_class(form)


##################
# DYNAMIC FIELDS #
##################
class DynamicField:
    '''
    A special field mixin that overrides native `get_attribute` method
    on Field and makes it work with dynamic fields of the Form.
    '''
    def get_attribute(self, instance):
        for attr in self.source_attrs:
            try:
                instance = getattr(instance, attr)
            except AttributeError:
                return instance.get_field(attr).value


class DynamicCharField(DynamicField, drf_fields.CharField):
    pass


class DynamicBooleanField(DynamicField, drf_fields.BooleanField):
    pass


class DynamicChoiceField(DynamicField, drf_fields.ChoiceField):
    pass


class DynamicJSONField(DynamicField, drf_fields.JSONField):
    pass


##############
# FORM: v1.0 #
##############
class FormSerializerV10(serializers.Serializer):
    serializer_field_mapping = {
        FieldTypes.INPUT: DynamicCharField,
        FieldTypes.TEXTAREA: DynamicCharField,
        FieldTypes.CHECKBOX: DynamicBooleanField,
        FieldTypes.RADIO: DynamicChoiceField,
        FieldTypes.SELECT: DynamicChoiceField,
        FieldTypes.FILE: drf_fields.FileField,
    }
    multi_checkbox_field = DynamicJSONField

    #################### INIT: ####################

    def __init__(
        self,
        *args,
        template=None,
        referral=None,
        accept_files=False,
        **kwargs
    ):
        '''
        :param `accept_files`: Whether this serializer will include file fields in the form.
        '''
        super().__init__(*args, **kwargs)

        self.accept_files = accept_files
        # File and note fields will be ignored
        self.ignore_fields = []

        if self.instance:
            assert isinstance(
                self.instance, Form
            ), ('The instance must be a %s object' % Form.__name__)
            self.template = self.instance.template
            self.referral = self.instance.referral
        else:
            self.template = template
            self.referral = referral

    #################### DYNAMIC FIELDS: ####################

    def get_fields(self):
        fields = OrderedDict()
        declared_fields = super().get_fields()
        fields.update(declared_fields)

        # Since the model fields are dynamic we cannot build
        # serializer fields without a template. Most of the
        # time the instance will be given to the serializer
        # and the template will be set up inside `__init__()`
        if not self.template:
            return fields

        # Build fields as per the template
        for field in self.template.fields.all():
            # Usually file fields are handled by a separate attachments endpoint
            # and are skipped for the form, but in case of external referrals
            # we must include them
            if field.type == FieldTypes.FILE:
                # For file fields we actually need to build 2 fields:
                # one for the file itself and another for the note
                if self.accept_files:
                    # We need to create a dummy field in order to render it,
                    # but it won't be saved to the database
                    note_field = FieldDefinition(
                        template=field.template,
                        type=FieldTypes.INPUT,
                        display_name='N/A',
                        order=field.order,
                        meta={'name': field.name + '_note'}
                    )

                    for i in range(field.meta.get('max_files', 1)):
                        field_name = f'{field.name}[{i}]'
                        fields[field_name] = self.build_field(
                            field, field_name=field_name
                        )
                        # We add fields to ignored so they're skipped during `update()`
                        self.ignore_fields.append(field_name)

                        # Reuse name variable and create note field
                        field_name = field.name + r'{note}' + f'[{i}]'
                        fields[field_name] = self.build_field(
                            note_field, field_name=field_name
                        )
                        # We add fields to ignored so they're skipped during `update()`
                        self.ignore_fields.append(field_name)

                # Whether we accept files or not - continue
                continue

            # Fields marked as `is_switch` are display-only and
            # should not be saved to the database
            if 'is_switch' in field.meta:
                continue

            fields[field.name] = self.build_field(field)

        return fields

    def build_field(self, field, field_name=None):
        if field.is_multi_checkbox:
            field_class = self.multi_checkbox_field
        else:
            field_class = self.serializer_field_mapping[field.type]
        field_kwargs = self.get_field_kwargs(field)
        field_obj = field_class(**field_kwargs)
        return field_obj

    def get_field_kwargs(self, field):
        meta = field.meta
        kwargs = {}

        # Conditional fields never have `required` flag set on the field,
        # instead they are validated in the `validate()`. This is done
        # to avoid requiring fields when their visibility condition isn't met
        kwargs['required'] = (
            not self.is_conditional_field(meta)
            and meta.get('required', False)
        )

        # `allow_null` defaults to inverse of `required`,
        # but can be overridden in the `validation` directive
        kwargs['allow_null'] = meta.get('validation', {})\
            .get('allow_null', not kwargs['required'])

        # Text fields, `allow_blank` also defaults to inverse of `required`
        if field.type in (FieldTypes.INPUT, FieldTypes.TEXTAREA):
            kwargs['allow_blank'] = meta.get('validation', {})\
                .get('allow_blank', not kwargs['required'])

        # Always show required error over blank & null errors
        kwargs['error_messages'] = {
            'null': utils.FIELD_REQUIRED_MSG,
            'blank': utils.FIELD_REQUIRED_MSG,
        }

        # Choice fields
        if field.type in (FieldTypes.RADIO, FieldTypes.SELECT):
            assert 'options' in meta, (
                '`%s` and `%s` fields must have array of `options`' %
                (FieldTypes.RADIO, FieldTypes.SELECT)
            )
            # Transform options into a list of tuples
            kwargs['choices'] = []
            for option in meta['options']:
                kwargs['choices'].append((option['value'], option['display']))

        return kwargs

    #################### VISIBILITY: ####################

    def is_conditional_field(self, field_meta):
        return 'visibility' in field_meta

    def parse_visiblity_value(self, value):
        if value in ('true', 'True', True):
            return 'True'
        if value in ('false', 'False', False):
            return 'False'
        if value in ('null', 'None', None):
            return 'None'
        if isinstance(value, int):
            return value

        # Otherwise we expect a string wrapped in extra quotes
        return value

    def convert_visiblity_value(self, value):
        if value is True:
            return 'True'
        if value is False:
            return 'False'
        if value is None:
            return 'None'
        if isinstance(value, int):
            return value

        # Othwerwise we wrap the string in extra quotes
        return f'"{value}"'

    def retrieve_field_value(self, serializer, field_name):
        '''
        Looks up the value of a field on the serializer in the
        submitted data or falls back to the instance data.
        '''
        value = None
        if hasattr(serializer, 'initial_data'):
            value = serializer.initial_data.get(field_name, None)
        if not value and serializer.instance:
            if isinstance(serializer.instance, Form):
                # If the instance is a Form object it uses
                # `get_field()` method to get field values
                value = serializer.instance.get_field(field_name).value
            else:
                # Otherwise this method is being used on the parent serializer's 
                # instance, so we fallback to the usual `getattr()`
                value = getattr(serializer.instance, field_name, None)
        return value

    def build_visibility_equation(
        self, field_value, sign, desired_value
    ) -> str:
        '''
        We parse values to get evaluatable equation string. Example: 

        `'ROUTN' == 'URGNT'`
        '''
        return '%s %s %s' % (
            self.parse_visiblity_value(field_value), sign,
            self.parse_visiblity_value(desired_value)
        )

    def get_meta_visibility(self, field) -> list:
        return field.meta.get('visibility', None)

    def visibility_condition_met(self, field, condition) -> bool:
        if condition:
            field = self.template.fields.filter(meta__name=condition[0]
                                                ).first()

            # Because switches never have a value saved in the
            # database we always default them to True and base
            # the equation off of that
            if field and field.meta.get('is_switch', False):
                field_value = True
            else:
                field_value = self.retrieve_field_value(self, condition[0])

            field_value = self.convert_visiblity_value(field_value)
            triplex = [field_value, condition[1], condition[2]]
            if not eval(self.build_visibility_equation(*triplex)):
                return False

        return True

    #################### TO INTERNAL VALUE: ####################

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.
        """
        utils.assert_data_is_mapping(self, data)

        ret = OrderedDict()
        errors = OrderedDict()
        fields = self._writable_fields

        for field in fields:
            validate_method = getattr(
                self, 'validate_' + field.field_name, None
            )
            primitive_value = field.get_value(data)

            try:
                validated_value = field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except serializers.ValidationError as exc:
                errors[field.field_name] = exc.detail
            except DjangoValidationError as exc:
                errors[field.field_name] = drf_fields.get_error_detail(exc)
            except drf_fields.SkipField:
                pass
            else:
                ret[field.field_name] = validated_value

        if errors:
            utils.raise_custom(errors)

        return ret

    #################### VALIDATION: ####################

    def validate(self, attrs):
        errors = {}

        if self.template:
            fields = self.template.fields.all()

            # Do additional field-specific validation
            for field in fields:
                # Require conditional fields
                if self.is_conditional_field(field.meta):
                    is_required = field.meta.get('required', False)
                    is_visible = self.visibility_condition_met(
                        field, self.get_meta_visibility(field)
                    )
                    has_value = (
                        field.name in attrs and attrs[field.name] is not None
                        and attrs[field.name] is not ''
                    )

                    if is_required and is_visible and not has_value:
                        utils.merge_required(errors, field.name)

                if field.name not in attrs:
                    continue

                # MULTI-CHECKBOXES:
                if field.is_multi_checkbox and attrs[field.name] is not None:
                    # Multi checkboxes only accept JSON arrays
                    if not isinstance(attrs[field.name], list):
                        msg = 'A valid JSON array is required'
                        utils.merge_field(errors, field.name, msg)
                        continue

                    # If allow blank is false we check for empty array
                    meta = field.meta
                    if (
                        'validation' in meta
                        and 'allow_blank' in meta['validation']
                        and not meta['validation']['allow_blank']
                        and not attrs[field.name]
                    ):
                        utils.merge_required(errors, field.name)
                        continue

                    # Lastly, we check whether sent values in array a valid
                    allowed_options = [x['value'] for x in meta['options']]
                    for value in attrs[field.name]:
                        if value not in allowed_options:
                            msg = f'"{value}" is not a valid option'
                            utils.merge_field(errors, field.name, msg)

                    continue

        if errors:
            utils.raise_custom(errors)

        return attrs

    #################### UPDATE: ####################

    def update(self, instance, validated_data):
        for field_name, value in validated_data.items():
            # If the form accepts file fields they will be
            # added to `ignore_fields` list
            if field_name in self.ignore_fields:
                continue

            field = instance.get_field(field_name)
            field.value = value
            field.save()

        return instance


############################
# FORM REPRESENTATOR: v1.0 #
############################
class FormRepresentatorV10(FormSerializerV10):
    field_structure = [
        # Forwardable
        'name',
        'type',
        'multiple',
        'is_switch',
        'value',
        'representation',
    ]
    field_repr_structure = [
        # Forwardable
        'columns',
        'label',
        'value',
        # Behavioural
        '__value_attributes',
    ]
    section_structure = [
        # Forwardable
        'title',
        'representation',
        'fields',
    ]
    section_repr_structure = [
        'title',
        'hide_title',
        'title_type',
    ]

    #################### REPRESENTATION: ####################

    def build_section_repr_clause(self, repr_clause):
        result = {}

        for key in self.section_repr_structure:
            if key in repr_clause:
                result[key] = repr_clause[key]

        return result

    def build_field_repr_clause(self, repr_meta, field):
        result = {}

        for key in self.field_repr_structure:
            # Inherit columns from field meta if not present in representation
            # otherwise default to 12
            if key == 'columns':
                result[key] = (
                    repr_meta.get(key, None)
                    or field.definition.meta.get('columns', 12)
                )
                continue

            if key == 'value':
                # Multi checkboxes need to properly display their options
                if field.is_multi_checkbox and field.value:
                    result[key] = [
                        opt['display'] for value in field.value
                        for opt in field.definition.meta['options']
                        if value == opt['value']
                    ]
                else:
                    result[key] = field.get_value_display()
                continue

            # Some metas will have value attributes dict which may
            # contain definitions for all values, empty value and/or
            # individual values. We check each case and pass nested
            # attributes to the result dict. For example if we have:
            #
            # "__value_attributes": {
            #     "__all": {
            #         "display_value_as": "yes_no"
            #     }
            # }
            #
            # Then `display_value_as` will end up in the result dict
            # regardless of what value the field holds
            if key == '__value_attributes' and key in repr_meta:
                for value in repr_meta[key]:
                    if value == '__all':
                        result.update(repr_meta[key]['__all'])
                    elif value == '__empty' and field.value == None:
                        result.update(repr_meta[key]['__empty'])
                    elif value == field.value:
                        result.update(repr_meta[key][field.value])
                continue

            if key in repr_meta:
                result[key] = repr_meta[key]

        return result

    def get_dependent_fields(self, all_fields, field_name) -> list:
        dependent_fields = []

        for field in all_fields.filter(meta__visibility__isnull=False):
            if field.meta['visibility'][0] == field_name:
                dependent_fields.append(field)

        return dependent_fields

    def get_switch_value(self, all_fields, switch_name, instance) -> bool:
        dependent_fields = self.get_dependent_fields(all_fields, switch_name)

        # If no dependent fields found then something is
        # wrong with the template, we just return false
        if not dependent_fields:
            return False

        # Otherwise we need to reverse visibility conditions
        # on all fields and determine switch value
        for field in dependent_fields:
            condition_met = self.visibility_condition_met(
                field, self.get_meta_visibility(field)
            )
            value = instance.get_field(field.name).value

            # The following, translated in human language means:
            # - if field shows up when switch=on and has a value; or
            # - if field shows up when switch=off and has no value
            if condition_met and value != None or not condition_met and value == None:
                return True

        return False

    def represent_fields(self, section_id, instance):
        result = []
        fields = instance.template.fields.all().order_by(
            'meta__representation__order', 'order'
        )

        for field_def in fields:
            field = instance.get_field(field_def.name)

            # Skip fields that don't belong to this section
            if field_def.meta['section_id'] != section_id:
                continue

            field_dict = OrderedDict()

            for key in self.field_structure:
                if key == 'value' and field_def.type != FieldTypes.FILE:
                    # Switch fields depend on their linked actual field
                    # so we have to check its value and set the switch
                    # to true/false
                    if field_def.meta.get('is_switch', False):
                        field_dict[key] = self.get_switch_value(
                            fields, field_def.name, instance
                        )
                        continue

                    # If not switch
                    field_dict[key] = field.value
                    continue

                if key == 'representation':
                    # Skip keys that aren't present on the field
                    if key not in field_def.meta:
                        continue

                    field_dict[key] = self.build_field_repr_clause(
                        field_def.meta[key], field
                    )
                    continue

                if key == 'type':
                    field_dict[key] = field_def.get_type_display()
                    continue

                if key in field_def.meta:
                    field_dict[key] = field_def.meta[key]

            result.append(field_dict)

        return result

    def represent_section(self, section_meta, instance):
        result = OrderedDict()

        for key in self.section_structure:
            if key == 'fields':
                fields = self.represent_fields(section_meta['id'], instance)
                result[key] = fields

            if key == 'representation':
                if key not in section_meta:
                    continue
                # Sometimes building clause will return an empty dict,
                # we want to skip the key in that case
                clause = self.build_section_repr_clause(section_meta[key])
                if clause:
                    result[key] = clause

            else:
                if key in section_meta:
                    result[key] = section_meta[key]

        return result

    def to_representation(self, instance):
        sections = []

        for section_meta in instance.template.meta['sections']:
            section = self.represent_section(section_meta, instance)
            sections.append(section)

        return {
            'tmsv': instance.template.get_tmsv_display(),
            'title': instance.template.meta.get('title', None),
            'representation':
                instance.template.meta.get('representation', None),
            'sections': sections,
        }


##############
# FORM: v1.1 #
##############
class FormSerializerV11(FormSerializerV10):
    '''
    '''
    def is_conditional_field(self, field_meta):
        return (
            super().is_conditional_field(field_meta)
            or 'parent_field' in field_meta
        )

    def get_meta_visibility(self, obj) -> dict:
        if isinstance(obj, FieldDefinition):
            if 'visibility' in obj.meta:
                return obj.meta['visibility']

        # We also expect sections to be passed here as dict,
        # e.g. when obj is a section
        elif isinstance(obj, dict):
            if 'visibility' in obj:
                return obj['visibility']

        return None

    def parent_visibility_condition_met(self, obj):
        # If this is a field we need to ensure its parents are visible
        if isinstance(obj, FieldDefinition):
            # First check the section
            for section in self.template.meta['sections']:
                if section['id'] == obj.meta['section_id']:
                    if not self.visibility_condition_met(
                        section, self.get_meta_visibility(section)
                    ):
                        return False
                    break

            # Then recursively go over parent fields
            if 'parent_field' in obj.meta:
                parent = self.template.fields.filter(
                    meta__name=obj.meta['parent_field']
                ).first()

                if not self.visibility_condition_met(
                    parent, self.get_meta_visibility(parent)
                ):
                    return False

        return True

    def referral_visibility_condition_met(self, obj, visibility_clause):
        if (
            isinstance(visibility_clause, dict)
            and 'referral' in visibility_clause
        ):
            for condition in visibility_clause['referral']:
                # In most cases a Form instance will be set on the serializer and the
                # reference to referral will be set in `__init__()`, but in some cases,
                # like external referrals, there's no Form instance, so we attempt to get
                # data from `initial_data` or `instance` on the parent serializer
                if self.referral:
                    value = getattr(self.referral, condition[0])
                elif self.parent:
                    value = self.retrieve_field_value(
                        serializer=self.parent, field_name=condition[0]
                    )
                else:
                    return False

                value = self.convert_visiblity_value(value)
                equation = self.build_visibility_equation(
                    field_value=value,
                    sign=condition[1],
                    desired_value=condition[2]
                )

                if not eval(equation):
                    return False

        return True

    def referrer_visibility_condition_met(self, obj, visibility_clause):
        if (
            isinstance(visibility_clause, dict)
            and 'referrer' in visibility_clause
        ):
            for condition in visibility_clause['referrer']:
                # In most cases a Form instance will be set on the serializer and the
                # reference to referral will be set in `__init__()`, so we can look up
                # the nested referrer object
                if self.referral and self.referral.referrer:
                    value = getattr(self.referral.referrer, condition[0])

                # But in some cases, like external referrals, there's no Form instance,
                # so we attempt to get the referrer data from the parent serializer
                elif self.parent:
                    # We also know that the parent serializer flattens its children and
                    # add a prefix with the parent object name and double underscore
                    # to the field names, e.g. "referrer__field_name", and we also know
                    # the parent serializer will never have an instance, because it
                    # doesn't support `update()` method. So we look up by the prefixed
                    # field
                    value = self.retrieve_field_value(
                        serializer=self.parent,
                        field_name=f'referrer__{condition[0]}'
                    )

                else:
                    return False

                value = self.convert_visiblity_value(value)
                equation = self.build_visibility_equation(
                    field_value=value,
                    sign=condition[1],
                    desired_value=condition[2]
                )

                if not eval(equation):
                    return False

        return True

    def template_visibility_condition_met(self, obj, visibility_clause):
        if (
            isinstance(visibility_clause, dict)
            and 'template' in visibility_clause
        ):
            for condition in visibility_clause['template']:
                parent = self.template.fields.filter(meta__name=condition[0]
                                                     ).first()

                # Because switches never have a value saved in the
                # database we always default them to True and base
                # the equation off of that
                if parent and parent.meta.get('is_switch', False):
                    parent_value = True
                else:
                    parent_value = self.retrieve_field_value(
                        self, condition[0]
                    )

                parent_value = self.convert_visiblity_value(parent_value)
                triplex = [parent_value, condition[1], condition[2]]
                if not eval(self.build_visibility_equation(*triplex)):
                    return False

        return True

    def visibility_condition_met(self, obj, clause) -> bool:
        '''
        Since v1.1 `visibility` notation changed to the following:

        ```
        'visibility': {
            'referral': [
                [
                    'external_submitter_type',
                    '==',
                    '"PATIENT"'
                ]
            ],
            'template': [[...],]
        }
        ```
        '''
        if not self.parent_visibility_condition_met(obj):
            return False

        if not self.referrer_visibility_condition_met(obj, clause):
            return False

        if not self.referral_visibility_condition_met(obj, clause):
            return False

        if not self.template_visibility_condition_met(obj, clause):
            return False

        return True


############################
# FORM REPRESENTATOR: v1.1 #
############################
class FormRepresentatorV11(FormSerializerV11, FormRepresentatorV10):
    '''
    '''

    #################### VISIBILITY: ####################

    def get_representation_clause(self, obj):
        if isinstance(obj, FieldDefinition):
            return obj.meta.get('representation', {})
        # We also expect sections to be passed here as dict,
        # e.g. when obj is a section
        elif isinstance(obj, dict):
            return obj.get('representation', {})

        return {}

    def get_repr_visibility_behaviour(self, obj):
        '''
        Determine visibility of the field in representation. 
        '''
        return self.get_representation_clause(obj).get(
            '__visibility_behaviour', 'persist'
        )

    def get_repr_visibility_clause(self, obj):
        return self.get_representation_clause(obj).get('__visibility', None)

    def visible_in_representation(self, obj) -> bool:
        '''
        Recursively check parent fields and section to determine whether this
        field should shod up in representation.
        '''
        # Grab representation visibility behaviour value
        behaviour = self.get_repr_visibility_behaviour(obj)

        if behaviour == 'persist':
            # If this is a field we need to ensure its parents are visible
            if isinstance(obj, FieldDefinition):
                # First check the section
                for section in self.template.meta['sections']:
                    if section['id'] == obj.meta['section_id']:
                        # This is a separate recursion from `visibility_condition_met()`,
                        # because it needs to consider the visibility behaviour, although
                        # this recursion relies on `visibility_condition_met()`
                        if not self.visible_in_representation(section):
                            return False
                        break

                # Then recursively go over parent fields
                if 'parent_field' in obj.meta:
                    parent = self.template.fields.filter(
                        meta__name=obj.meta['parent_field']
                    ).first()
                    # Read comment on line #745
                    if not self.visible_in_representation(parent):
                        return False

        if behaviour == 'follow_meta':
            # Behaviour is determined by the meta, check conditions
            if not self.visibility_condition_met(
                obj, self.get_meta_visibility(obj)
            ):
                return False

        if behaviour == 'custom':
            # Section has a custom behaviour, check here
            custom_definition = self.get_repr_visibility_clause(obj)
            if not self.visibility_condition_met(obj, custom_definition):
                return False

        return True

    #################### REPRESENTATION: ####################

    def get_dependent_fields(self, all_fields, field_name) -> list:
        dependent_fields = []

        for field in all_fields.filter(meta__visibility__isnull=False):
            if 'template' in field.meta['visibility']:
                for triplex in field.meta['visibility']['template']:
                    if triplex[0] == field_name:
                        dependent_fields.append(field)

        return dependent_fields

    def get_switch_value(self, all_fields, switch_name, instance) -> bool:
        dependent_fields = all_fields.filter(meta__parent_field=switch_name)

        # If no dependent fields found then something is
        # wrong with the template, we just return false
        if not dependent_fields:
            return False

        # Otherwise we need to check if any nested field
        # has a value
        for field in dependent_fields:
            if instance.get_field(field.name).value:
                return True

        return False

    def represent_fields(self, section_id, instance):
        result = super().represent_fields(section_id, instance)
        new_result = []

        for field_repr in result:
            field = instance.template.fields.filter(
                meta__name=field_repr['name']
            ).first()

            if not self.visible_in_representation(field):
                continue

            new_result.append(field_repr)

        return new_result

    def to_representation(self, instance):
        sections = []

        # We will filter out setions that are not supposed to be rendered
        for section_meta in instance.template.meta['sections']:
            if not self.visible_in_representation(section_meta):
                continue

            section = self.represent_section(section_meta, instance)
            sections.append(section)

        return {
            'tmsv': instance.template.get_tmsv_display(),
            'title': instance.template.meta.get('title', None),
            'representation':
                instance.template.meta.get('representation', None),
            'sections': sections,
        }
