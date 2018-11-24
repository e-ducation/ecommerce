# -*- coding: utf-8 -*-

import datetime
import random
from ecommerce.extensions.payment.processors import BasePaymentProcessor, HandledProcessorResponse
from ecommerce.extensions.payment.utils import create_trade_id, str_to_specify_digits
from payments.alipay.alipay import create_direct_pay_by_user


class AliPay(BasePaymentProcessor):

    NAME = 'alipay'
    DEFAULT_PROFILE_NAME = 'default'

    def __init__(self, site):
        super(AliPay, self).__init__(site)

    def get_transaction_parameters(self, basket, request=None, use_client_side_checkout=False, **kwargs):

        body = "BUY {amount} {currency}".format(amount=basket.total_incl_tax, currency=basket.currency)
        subject = "BUY COURSE"
        total_fee = basket.total_incl_tax
        approval_url = self.get_pay_html(body, subject, total_fee, 'localhost', 22)

        print '^' * 100
        print unicode(basket.total_incl_tax),
        print basket.currency,
        print '^' * 100
        parameters = {
            'payment_page_url': approval_url,
        }
        return parameters

    def get_pay_html(self, body, subject, total_fee, http_host, order_id):
        """
        get alipay html
        # 支付信息，订单号必须唯一
        """
        # extra_common_param = settings.LMS_ROOT_URL + reverse("vip_purchase")

        extra_common_param = ''
        total_fee = str_to_specify_digits(str(total_fee))
        trade_id = create_trade_id(order_id)
        pay_html = create_direct_pay_by_user(
            trade_id,
            body,
            subject,
            total_fee,
            http_host,
            extra_common_param=extra_common_param
        )
        return pay_html

    def handle_processor_response(self, response, basket=None):
        return HandledProcessorResponse(
            transaction_id=1,
            total=1,
            currency='1',
            card_number=1,
            card_type=None
        )


    def issue_credit(self, order_number, basket, reference_number, amount, currency):
        pass
