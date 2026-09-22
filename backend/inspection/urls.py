from django.urls import path

from inspection import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.list_view, name="list"),
    path("inspections/new/", views.create_view, name="create"),
    path("inspections/<int:pk>/", views.detail_view, name="detail"),
    path("inspections/<int:pk>/correct/", views.correct_view, name="correct"),
    path("inspections/<int:pk>/receipts/", views.receipt_book, name="receipt_book"),
    path("inspections/<int:pk>/receipts/issue/", views.issue_receipt, name="issue_receipt"),
    path("receipts/<int:pk>/", views.receipt_detail, name="receipt_detail"),
    path("receipts/<int:pk>/download/", views.receipt_download, name="receipt_download"),
]
