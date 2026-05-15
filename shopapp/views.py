from django.http import JsonResponse
from django.views import View


class SignInView(View):
    def post(self, request):
        # TODO: implement sign-in
        return JsonResponse({}, status=500)


class SignUpView(View):
    def post(self, request):
        # TODO: implement sign-up
        return JsonResponse({}, status=500)


class SignOutView(View):
    def post(self, request):
        # TODO: implement sign-out
        return JsonResponse({}, status=200)


class CategoryListView(View):
    def get(self, request):
        # TODO: return categories list
        return JsonResponse([], safe=False)


class CatalogView(View):
    def get(self, request):
        # TODO: return paginated catalog with filters
        return JsonResponse({"items": [], "currentPage": 1, "lastPage": 1})


class PopularProductsView(View):
    def get(self, request):
        # TODO: return top-8 popular products
        return JsonResponse([], safe=False)


class LimitedProductsView(View):
    def get(self, request):
        # TODO: return up to 16 limited edition products
        return JsonResponse([], safe=False)


class SalesView(View):
    def get(self, request):
        # TODO: return sales with pagination
        return JsonResponse({"items": [], "currentPage": 1, "lastPage": 1})


class BannersView(View):
    def get(self, request):
        # TODO: return banner products
        return JsonResponse([], safe=False)


class ProductDetailView(View):
    def get(self, request, pk):
        # TODO: return full product info
        return JsonResponse({})


class ProductReviewView(View):
    def post(self, request, pk):
        # TODO: add review, return all reviews
        return JsonResponse([], safe=False)


class TagsView(View):
    def get(self, request):
        # TODO: return tags (optionally filtered by category)
        return JsonResponse([], safe=False)


class BasketView(View):
    def get(self, request):
        # TODO: return basket contents
        return JsonResponse([], safe=False)

    def post(self, request):
        # TODO: add item to basket
        return JsonResponse([], safe=False)

    def delete(self, request):
        # TODO: remove item from basket
        return JsonResponse([], safe=False)


class OrdersView(View):
    def get(self, request):
        # TODO: return user orders
        return JsonResponse([], safe=False)

    def post(self, request):
        # TODO: create order from basket
        return JsonResponse({"orderId": 0})


class OrderDetailView(View):
    def get(self, request, pk):
        # TODO: return order details
        return JsonResponse({})

    def post(self, request, pk):
        # TODO: confirm order
        return JsonResponse({}, status=200)


class PaymentView(View):
    def post(self, request, pk):
        # TODO: process payment
        return JsonResponse({}, status=200)


class ProfileView(View):
    def get(self, request):
        # TODO: return user profile
        return JsonResponse({})

    def post(self, request):
        # TODO: update user profile
        return JsonResponse({})


class ProfilePasswordView(View):
    def post(self, request):
        # TODO: change password
        return JsonResponse({}, status=200)


class AvatarView(View):
    def post(self, request):
        # TODO: upload avatar
        return JsonResponse({}, status=200)
