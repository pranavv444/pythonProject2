from django.db import models

class GithubToken(models.Model):
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
