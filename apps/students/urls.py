from django.urls import path
from apps.students.import_views import DataImportWebUploadView

app_name = 'students'

urlpatterns = [
    path('import/', DataImportWebUploadView.as_view(), name='data_import'),
]
