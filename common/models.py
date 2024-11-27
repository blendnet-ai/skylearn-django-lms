from django.db import models


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating created_at and updated_at fields.
    """
    created_at = models.DateTimeField('Date created', auto_now_add=True)
    updated_at = models.DateTimeField('Date updated', auto_now=True)

    class Meta:
        abstract = True