import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends import s3boto3


class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to.

        Found at http://djangosnippets.org/snippets/976/

        This file storage solves overwrite on upload problem. Another
        proposed solution was to override the save method on the model
        like so (from https://code.djangoproject.com/ticket/11663):

        def save(self, *args, **kwargs):
            try:
                this = MyModelName.objects.get(id=self.id)
                if this.MyImageFieldName != self.MyImageFieldName:
                    this.MyImageFieldName.delete()
            except: pass
            super(MyModelName, self).save(*args, **kwargs)
        """

        # If the filename already exists, remove it as if it was a true file system
        path = os.path.join(settings.MEDIA_ROOT, name)
        if self.exists(path):
            os.remove(path)
        return name


class S3StaticStorage(s3boto3.S3StaticStorage):
    # Override some default settings for this S3 Storage backend. See the list of
    # options here: https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
    location = "static"
    is_gzipped = True
    querystring_auth = False
    s3_object_parameters = {"CacheControl": "public, max-age=604800"}
    default_acl = "public-read"


class S3PublicStorage(s3boto3.S3Boto3Storage):
    # Override some default settings for this S3 Storage backend. See the list of
    # options here: https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
    location = "public"
    querystring_auth = False
    default_acl = "public-read"
