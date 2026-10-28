from django.contrib import admin
from .models import Comment, CommentFile


class CommentFileInline(admin.TabularInline):
    model = CommentFile
    extra = 0
    raw_id_fields = ("created_by",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "content_type", "object_id", "created", "reply_to")
    list_filter = ("created", "content_type")
    search_fields = ("text", "created_by__username", "created_by__email")
    raw_id_fields = ("created_by", "reply_to", "mention")
    inlines = [CommentFileInline]


@admin.register(CommentFile)
class CommentFileAdmin(admin.ModelAdmin):
    list_display = ("id", "comment", "file", "created_by")
    search_fields = ("filename", "comment__text", "created_by__username")
    raw_id_fields = ("comment", "created_by")