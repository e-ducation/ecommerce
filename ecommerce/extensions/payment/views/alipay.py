
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import View
from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin

class AlipayPaymentExecutionView(EdxOrderPlacementMixin, View):

    def get(self, request):

        return redirect('http://www.qq.com')

    def post(self, request):

        return HttpResponse('success')
