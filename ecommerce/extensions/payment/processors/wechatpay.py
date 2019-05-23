# -*- coding:utf-8 -*-
import logging
import qrcode
import base64

from io import BytesIO
from decimal import Decimal
from urlparse import urljoin
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from ecommerce.core.url_utils import get_ecommerce_url
from ecommerce.extensions.payment.processors import BasePaymentProcessor, HandledProcessorResponse
from ecommerce.extensions.payment.utils import create_trade_id
from ecommerce.courses.utils import get_course_info_from_catalog
from payments.wechatpay.wxpay import WxPayConf_pub, UnifiedOrder_pub
from oscar.core.loading import get_model, get_class

PaymentProcessorResponse = get_model('payment', 'PaymentProcessorResponse')
Applicator = get_class('offer.applicator', 'Applicator')

logger = logging.getLogger(__name__)


class WechatPay(BasePaymentProcessor):

    NAME = 'wechatpay'
    DEFAULT_PROFILE_NAME = 'default'

    def __init__(self, site):
        super(WechatPay, self).__init__(site)

    @property
    def cancel_url(self):
        return get_ecommerce_url(self.configuration['cancel_checkout_path'])

    @property
    def error_url(self):
        return get_ecommerce_url(self.configuration['error_path'])

    def get_transaction_parameters(self, basket, request=None, use_client_side_checkout=False, **kwargs):
        """
        """
        # Get the basket, and make sure it belongs to the current user.
        try:
            basket = request.user.baskets.get(id=basket.id)
        except ObjectDoesNotExist:
            return {}

        try:
            # Freeze the basket so that it cannot be modified
            basket.strategy = request.strategy
            Applicator().apply(basket, request.user, request)
            # basket.freeze()
            if basket.total_incl_tax <= 0:
                return {}

            out_trade_no = create_trade_id(basket.id)
            try:
                course_data = get_course_info_from_catalog(request.site, basket.all_lines()[0].product)
                body = course_data.get('title')
            except Exception, e:
                logger.exception(e)
                body = 'buy course'
            order_price = basket.total_incl_tax
            total_fee = int(order_price * 100)
            attach_data = urljoin(get_ecommerce_url(), reverse('wechatpay:execute'))

            wxpayconf_pub = WxPayConf_pub()
            unifiedorder_pub = UnifiedOrder_pub()
            unifiedorder_pub.setParameter("body", body)
            unifiedorder_pub.setParameter("out_trade_no", out_trade_no)
            unifiedorder_pub.setParameter("total_fee", str(total_fee))
            unifiedorder_pub.setParameter("notify_url", wxpayconf_pub.NOTIFY_URL)
            unifiedorder_pub.setParameter("trade_type", "NATIVE")
            unifiedorder_pub.setParameter("attach", attach_data)

            code_url = unifiedorder_pub.getCodeUrl()
            img = qrcode.make(code_url)
            buf = BytesIO()
            img.save(buf, format="PNG")
            qrcode_img = base64.b64encode(buf.getvalue())
            if not PaymentProcessorResponse.objects.filter(processor_name=self.NAME, basket=basket).update(transaction_id=out_trade_no):
                self.record_processor_response({}, transaction_id=out_trade_no, basket=basket)

            parameters = {
                'qrcode_img': qrcode_img,
            }
            return parameters
        except Exception, e:
            logger.exception(e)
        return {}

    def handle_processor_response(self, response, basket=None):
        transaction_id = response.get('out_trade_no')
        PaymentProcessorResponse.objects.filter(
            processor_name=self.NAME,
            transaction_id=transaction_id
        ).update(response=response, basket=basket)

        total = Decimal(response.get('total_fee'))
        email = response.get('buyer_email')
        label = 'WechatPay ({})'.format(email) if email else 'WechatPay Account'
        return HandledProcessorResponse(
            transaction_id=transaction_id,
            total=total,
            currency='CNY',
            card_number=label,
            card_type=None
        )

    def issue_credit(self, order_number, basket, reference_number, amount, currency):
        pass
