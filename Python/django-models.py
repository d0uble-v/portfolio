'''
A couple of examples of project models.
'''

import uuid
import os.path
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings
from consultmed import choices
from .forms import FormTemplate
from .mixins import CryptoSecurePKModel


###########
# HELPERS #
###########
def uuid_hex():
    return uuid.uuid4().hex


def uuid_str():
    return str(uuid.uuid4())


def year_week_uuid(instance, filename):
    from os.path import splitext

    today = timezone.now()
    return '{year}/{week}/{name}{ext}'.format(
        year=today.year,
        week=today.isocalendar()[1],
        name=uuid_hex(),
        ext=splitext(filename)[1].lower()
    )


##############
# MEDIA FILE #
##############
class MediaFile(CryptoSecurePKModel):
    '''
    A generic model to store various types of files
    and their metadata.
    '''

    #################### CONSTANTS: ####################

    IMAGES = ['.jpeg', '.jpg', '.png']
    FILES = ['.pdf', '.doc', '.docx']

    #################### FIELDS: ####################

    mime_type = models.CharField(max_length=75, null=True)
    original_name = models.CharField(max_length=150, null=True)
    _image = models.ImageField(upload_to=year_week_uuid, null=True)
    _file = models.FileField(upload_to=year_week_uuid, null=True)
    created_at = models.DateTimeField()
    meta = models.JSONField(null=True)

    def save(self, *args, **kwargs):
        self.created_at = timezone.now()
        return super().save(*args, **kwargs)

    def save_original_info(self, original_file):
        '''
        Saves original file name and mime type.
        '''
        self.original_name = original_file.name
        self.mime_type = original_file.content_type

    def is_image(self):
        return self._image is not None

    def is_file(self):
        return self._file is not None

    @property
    def file(self):
        return self._image or self._file

    @file.setter
    def file(self, obj):
        self.save_original_info(obj)
        name, extension = os.path.splitext(obj.name)

        if extension in MediaFile.IMAGES:
            self._image = obj
        elif extension in MediaFile.FILES:
            self._file = obj
        else:
            raise Exception('File type `%s` is not allowed' % extension)


############
# SETTINGS #
############
class Settings(models.Model):
    '''
    A singleton model to store project's settings.
    '''
    default_user_groups = models.ManyToManyField(
        Group, related_name='+', blank=True
    )
    default_doctor_groups = models.ManyToManyField(
        Group, related_name='+', blank=True
    )
    default_specialist_groups = models.ManyToManyField(
        Group, related_name='+', blank=True
    )
    default_specialist_in_training_groups = models.ManyToManyField(
        Group, related_name='+', blank=True
    )
    default_admin_groups = models.ManyToManyField(
        Group, related_name='+', blank=True
    )

    # Staff emails
    staff_emails = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Settings'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_default_form_templates(
        self, template_type=choices.ReferralTypes.IN_APP
    ):
        return FormTemplate.objects.filter(
            organisation=None,
            establishment=None,
            is_current=True,
            type=template_type,
        )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def get_staff_emails(self):
        return self.staff_emails.split()