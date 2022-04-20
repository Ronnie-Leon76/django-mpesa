import os
import socket
import json
import requests
import datetime

from django.urls import reverse
import requests
from requests.auth import HTTPBasicAuth
from base64 import b64encode
from .models import PaymentTransaction

# import env settings
from decouple import config

consumer_key = config('CONSUMER_KEY')
consumer_secret = config('CONSUMER_SECRET')

HOST_NAME = config('HOST_NAME')
PASS_KEY = config('PASS_KEY')
shortcode = config('SHORT_CODE')
SAFARICOM_API = config('SAFARICOM_API')

# Applies for LipaNaMpesaOnline Payment method


def generate_pass_key():
    time_now = datetime.datetime.now().strftime("%Y%m%d%H%I%S")
    s = shortcode + PASS_KEY + time_now
    encoded = b64encode(s.encode('utf-8')).decode('utf-8')


def get_token():
    api_URL = "{}/oauth/v1/generate?grant_type=client_credentials".format(
        SAFARICOM_API)

    r = requests.get(api_URL, auth=HTTPBasicAuth(
        consumer_key, consumer_secret))
    jonresponse = json.loads(r.content)
    access_token = jonresponse['access_token']
    print(access_token)
    return access_token


def check_payment_status(checkout_request_id):
    access_token = get_token()
    time_now = datetime.datetime.now().strftime("%Y%m%d%H%I%S")

    s = shortcode + PASS_KEY + time_now
    encoded = b64encode(s.encode('utf-8')).decode('utf-8')

    api_url = "{}/mpesa/stkpushquery/v1/query".format(SAFARICOM_API)
    headers = {
        "Authorization": "Bearer %s" % access_token,
        "Content-Type": "application/json",
    }
    request = {
        "BusinessShortCode": shortcode,
        "Password": encoded,
        "Timestamp": time_now,
        "CheckoutRequestID": checkout_request_id
    }
    response = requests.post(api_url, json=request, headers=headers)
    json_response = json.loads(response.text)
    if 'ResponseCode' in json_response and json_response["ResponseCode"] == "0":
        result_code = json_response['ResultCode']
        response_message = json_response['ResultDesc']
        return {
            "result_code": result_code,
            "status": result_code == "0",
            "message": response_message
        }
    else:
        raise Exception("Error sending MPesa stk push", json_response)


def sendSTK(phone_number, amount, orderId=0, transaction_id=None):
    access_token = get_token()
    time_now = datetime.datetime.now().strftime("%Y%m%d%H%I%S")

    s = shortcode + PASS_KEY + time_now
    encoded = b64encode(s.encode('utf-8')).decode('utf-8')

    api_url = "{}/mpesa/stkpush/v1/processrequest".format(SAFARICOM_API)
    headers = {
        "Authorization": "Bearer %s" % access_token,
        "Content-Type": "application/json",
    }
    print("Phonenumber: {}, Amount: {}".format(phone_number, amount))
    request = {
        "BusinessShortCode": shortcode,
        "Password": encoded,
        "Timestamp": time_now,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": "{}/mpesa/confirm/".format(HOST_NAME),
        "AccountReference": phone_number,
        "TransactionDesc": "Payment for {}".format(phone_number)
    }

    response = requests.post(api_url, json=request, headers=headers)
    json_response = json.loads(response.text)
    if json_response["ResponseCode"] == "0":
        checkoutId = json_response["CheckoutRequestID"]
        if transaction_id:
            transaction = PaymentTransaction.objects.filter(id=transaction_id)
            transaction.checkoutRequestID = checkoutId
            transaction.save()
            # After creating the transaction let it also query to see if the transaction was complete
            # If it's complete, it then updates to is_successful and isFinished
            # This will make it easier for me to update my orders to paid
            return check_payment_status(checkoutId)
            # return transaction.id
        else:
            transaction = PaymentTransaction.objects.create(phone_number=phone_number, checkoutRequestID=checkoutId,
                                                            amount=amount, order_id=orderId)
            transaction.save()
            # After creating the transaction let it also query to see if the transaction was complete
            # If it's complete, it then updates to is_successful and isFinished
            # This will make it easier for me to update my orders to paid
            # How long does it take to complete a transaction? Maybe we can set a timeout
            return check_payment_status(checkoutId)
            # return transaction.id

    else:
        raise Exception("Error sending MPesa stk push", json_response)


# Is this how I query from the installed Django-M-pesa library
# from mpesa.models import PaymentTransaction
# And performing a query to the PaymentTransaction Model
    """def updateOrderToPaid(request, pk):
    user = request.user
    order = Order.objects.get(_id=pk)
    paymentTransaction = PaymentTransaction.objects.get(order_id=str(pk))
    # paymentTransaction = get_object_or_404(transaction,order_id=pk)
    checkoutRequestId = paymentTransaction.checkout_request_id
    print(check_payment_status(checkoutRequestId))
    """
