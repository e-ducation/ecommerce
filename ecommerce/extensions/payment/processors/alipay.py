# -*- coding: utf-8 -*-
import logging

from decimal import Decimal
from urlparse import urljoin
from django.urls import reverse
from oscar.core.loading import get_model
from ecommerce.core.url_utils import get_ecommerce_url
from ecommerce.extensions.payment.processors import BasePaymentProcessor, HandledProcessorResponse
from ecommerce.extensions.payment.utils import create_trade_id, str_to_specify_digits
from ecommerce.courses.utils import get_course_info_from_catalog
from payments.alipay.alipay import create_direct_pay_by_user

PaymentProcessorResponse = get_model('payment', 'PaymentProcessorResponse')

logger = logging.getLogger(__name__)


class AliPay(BasePaymentProcessor):

    NAME = 'alipay'
    DEFAULT_PROFILE_NAME = 'default'

    def __init__(self, site):
        super(AliPay, self).__init__(site)

    @property
    def cancel_url(self):
        return get_ecommerce_url(self.configuration['cancel_checkout_path'])

    @property
    def error_url(self):
        return get_ecommerce_url(self.configuration['error_path'])

    def get_transaction_parameters(self, basket, request=None, use_client_side_checkout=False, **kwargs):
        """
        approval_url
        """
        trade_id = create_trade_id(basket.id)
        try:
            course_data = get_course_info_from_catalog(request.site, basket.all_lines()[0].product)
            subject = body = course_data.get('title')
        except Exception, e:
            logger.exception(e)
            subject = body = 'buy course'
        total_fee = str_to_specify_digits(str(basket.total_incl_tax))
        http_host = request.META.get('HTTP_HOST')
        extra_common_param = urljoin(get_ecommerce_url(), reverse('alipay:execute'))

        approval_url = create_direct_pay_by_user(
            trade_id,
            body,
            subject,
            total_fee,
            http_host,
            extra_common_param=extra_common_param
        )
        if not PaymentProcessorResponse.objects.filter(processor_name=self.NAME, basket=basket).update(transaction_id=trade_id):
            self.record_processor_response({}, transaction_id=trade_id, basket=basket)

        parameters = {
            'payment_page_url': approval_url,
        }
        return parameters

    def handle_processor_response(self, response, basket=None):
        """
        """
        transaction_id = response.get('out_trade_no')
        PaymentProcessorResponse.objects.filter(
            processor_name=self.NAME,
            transaction_id=transaction_id
        ).update(response=response, basket=basket)

        total = Decimal(response.get('total_fee'))
        email = response.get('buyer_email')
        label = 'AliPay ({})'.format(email) if email else 'AliPay Account'
        return HandledProcessorResponse(
            transaction_id=transaction_id,
            total=total,
            currency='CNY',
            card_number=label,
            card_type=None
        )

    def issue_credit(self, order_number, basket, reference_number, amount, currency):
        pass
