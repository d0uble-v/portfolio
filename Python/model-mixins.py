'''
A list of handy mixins with various functions used by the project's models.
'''

import threading
import time
import random
from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string
from django.utils import timezone


###########
# HELPERS #
###########
def make_unique_bigint_pk():
    '''
    DEPRECATED.

    Kept for historical reasons, i.e. used by one of migrations.
    Inspired by http://instagram-engineering.tumblr.com/post/10853187575/sharding-ids-at-instagram
    '''
    t = int(time.time()) - settings.BIPK_START_TIME
    u = random.SystemRandom().getrandbits(23)
    return (t << 20) | u


#########################
# GET ACTING USER MIXIN #
#########################
class GetActingUserMixin:
    '''
    A mixin that adds `get_acting_user` to a model, allowing it to
    get a reference to the User performing CRUD operations.

    `ActingUserTrackingMiddleware` must be added to the list of
    middleware in settings.
    '''
    thread = threading.local()

    def get_acting_user(self):
        try:
            return self.thread.request.user
        except AttributeError:
            msg = 'Acting user tracking middleware must be enabled in settings.'
            raise Exception(msg)


#############################
# TRACK ADDED/UPDATED MIXIN #
#############################
class TrackAddedUpdatedMixin(GetActingUserMixin, models.Model):
    '''
    An extension on top of GetActingUserMixin. Declares fields and tracks
    the following model fields:
    - `added_by`
    - `added_at`
    - `updated_by`
    - `updated_at`
    '''
    added_by = models.ForeignKey(
        'auth.User',
        related_name='+',
        null=True,
        on_delete=models.PROTECT,
    )
    added_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(
        'auth.User',
        related_name='+',
        null=True,
        on_delete=models.PROTECT,
    )
    updated_at = models.DateTimeField(null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.added_at = timezone.now()
            # Sometimes creator might be overwritten
            if not self.added_by:
                self.added_by = self.get_acting_user()
        else:
            self.updated_at = timezone.now()
            self.updated_by = self.get_acting_user()

        super().save(*args, **kwargs)


######################
# FULL ADDRESS MIXIN #
######################
class FullAddressMixin:
    '''
    A mixin for models that have address fields 
    to join them into a full address string.
    '''
    @property
    def full_address(self):
        parts = [
            self.address1,
            self.address2,
            self.city,
            self.state,
            self.postcode,
        ]
        return ' '.join([i for i in parts if i])


###################
# FULL NAME MIXIN #
###################
class FullNameMixin:
    '''
    A mixin for models that have first and last name fields
    to join them into a full name string.
    '''
    @property
    def full_name(self):
        return '%s %s' % (self.first_name, self.last_name)


##########################
# CRYPTO SECURE PK MODEL #
##########################
class CryptoSecurePKModel(models.Model):
    '''
    A model with a unique, big integer primary key.
    '''
    id = models.CharField(
        primary_key=True,
        max_length=12,
        editable=False,
        default=get_random_string,
    )

    class Meta:
        abstract = True


############################
# TRACK FIELD CHANGE MIXIN #
############################
class TrackFieldChangeMixin(models.Model):
    '''
    A mixin that allows tracking field changes on a model instance.
    '''
    class Meta:
        abstract = True

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)

        # Save original values, when model is loaded from database,
        # in a separate attribute on the model
        instance._initial_data = dict(zip(field_names, values))

        return instance

    def field_changed(self, name) -> bool:
        ''' 
        Check whether the field value changed.

        IMPORTANT: For FK fields use the `*_id` field for 
        speed and to avoid an endless recursive object loading.
        '''
        # TODO: Implement FK fields check and raise error
        if not hasattr(self, '_initial_data'):
            return False
        return getattr(self, name) != self._initial_data.get(name)
