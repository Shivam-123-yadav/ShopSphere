from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path("products/", views.product_list, name="product_list"),
    path("checkout/", views.checkout_view, name="checkout"),
    # path("cashfree/payment-success/", views.cashfree_payment_success, name="cashfree_payment_success"),
    path("profile/", views.profile_view, name="profile"),
    path('api/search/', views.api_search_products, name='api_search_products'),
    path("upload-products/", views.upload_products_csv, name="upload_products"),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('about/', views.about_view, name='about'),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    path('category/<slug:slug>/', views.category_view, name='category'),
    path('categories/', views.all_categories_view, name='categories'),
]
