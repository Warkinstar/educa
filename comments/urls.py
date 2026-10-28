from django.urls import path
from comments import views

app_name = "comments"

urlpatterns = [
    path(
        "comments/<str:app_label>/<str:model_name>/upload-file/",
        views.UnrelatedCommentFileUploadView.as_view(),
        name="unrelated_comment_file_upload",
    ),
    path(
        "comment/unrelated-comment-files-info/",
        views.UnrelatedCommentFileListView.as_view(),
        name="unrelated_comment_file_list",
    ),
    path(
        "unrelated-comment-file/<uuid:public_id>/delete/",
        views.UnrelatedCommentFileDeleteView.as_view(),
        name="unrelated_comment_file_delete",
    ),
    path(
        "comments/<str:app_label>/<str:model_name>/<uuid:public_id>/comment-create/",
        views.CommentCreateView.as_view(),
        name="comment_create",
    ),
    path(
        "comments/<uuid:public_id>/delete/",
        views.CommentDeleteView.as_view(),
        name="comment_delete",
    ),
    path(
        "comment-file/<uuid:public_id>/download/",
        views.CommentFileDownloadView.as_view(),
        name="comment_file_download",
    ),
]