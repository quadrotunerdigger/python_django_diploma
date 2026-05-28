from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("sign-in", views.SignInView.as_view(), name="sign-in"),
    path("sign-up", views.SignUpView.as_view(), name="sign-up"),
    path("sign-out", views.SignOutView.as_view(), name="sign-out"),
    # Catalog
    path("categories", views.CategoryListView.as_view(), name="categories"),
    path("catalog", views.CatalogView.as_view(), name="catalog"),
    path("products/popular", views.PopularProductsView.as_view(), name="products-popular"),
    path("products/limited", views.LimitedProductsView.as_view(), name="products-limited"),
    path("sales", views.SalesView.as_view(), name="sales"),
    path("banners", views.BannersView.as_view(), name="banners"),
    # Product detail
    path("product/<int:pk>", views.ProductDetailView.as_view(), name="product-detail"),
    path("product/<int:pk>/review", views.ProductReviewView.as_view(), name="product-review"),
    path("product/<int:pk>/reviews", views.ProductReviewView.as_view(), name="product-reviews"),
    # Tags
    path("tags", views.TagsView.as_view(), name="tags"),
    # Basket
    path("basket", views.BasketView.as_view(), name="basket"),
    # Orders
    path("orders", views.OrdersView.as_view(), name="orders"),
    path("orders/<int:pk>", views.OrderDetailView.as_view(), name="order-detail"),
    path("order/<int:pk>", views.OrderDetailView.as_view(), name="order-detail-alt"),
    # Payment
    path("payment/<int:pk>", views.PaymentView.as_view(), name="payment"),
    # Profile
    path("profile", views.ProfileView.as_view(), name="profile"),
    path("profile/password", views.ProfilePasswordView.as_view(), name="profile-password"),
    path("profile/avatar", views.AvatarView.as_view(), name="profile-avatar"),
]
