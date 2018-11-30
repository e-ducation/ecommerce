import logging

from django.http import HttpResponse
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from oscar.core.loading import get_model
from ecommerce.extensions.payment.processors.wechatpay import WechatPay
from ecommerce.extensions.payment.views.alipay import AlipayPaymentExecutionView, AlipayPaymentResultView
from payments.wechatpay.wxpay import OrderQuery_pub

Basket = get_model('basket', 'Basket')
PaymentProcessorResponse = get_model('payment', 'PaymentProcessorResponse')

logger = logging.getLogger(__name__)


class WechatpayPaymentExecutionView(AlipayPaymentExecutionView):

    @property
    def payment_processor(self):
        return WechatPay(self.request.site)


class WechatpayPaymentResultView(AlipayPaymentResultView):

    @property
    def payment_processor(self):
        return WechatPay(self.request.site)


class WechatpayPaymentPageView(View):
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WechatpayPaymentPageView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        context = {
            'code_url': request.POST.get('code_url'),
            'basket_id': request.POST.get('basket_id'),
            'result_page': request.POST.get('request_page'),
        }
        return HttpResponse(context['code_url'])


class WechatpayOrderQuery(APIView):

    NOTPAY = 1
    PAID = 2

    def get(self, request, pk):
        status = self.NOTPAY
        try:
            basket = Basket.objects.get(owner=request.user, id=pk)
            if basket.status == 'Submitted':
                status = self.PAID
            else:
                status = self.wechatpay_query(basket)
        except Exception, e:
            logger.exception(e)

        return Response({
            'code': 0,
            'msg': '',
            'data': {
                'status': status
            },
        })

    @classmethod
    def wechatpay_query(cls, basket):
        '''
        '''
        orderquery_pub = OrderQuery_pub()
        pay_resp = PaymentProcessorResponse.objects.get(processor_name=WechatPay.NAME, basket=basket)
        resp = pay_resp.response
        orderquery_pub.setParameter('out_trade_no', pay_resp.transaction_id)
        trade_no = resp.get('trade_no')
        if trade_no:
            orderquery_pub.setParameter('transaction_id', trade_no)

        result = orderquery_pub.getResult()
        logger.info(result)
        if result.pop('sign') == orderquery_pub.getSign(result) and result.get('trade_state') == 'SUCCESS':
            return cls.PAID
        return cls.NOTPAY
