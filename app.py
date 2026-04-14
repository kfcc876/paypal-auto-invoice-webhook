import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# PayPal API Credentials (Set these in Render Environment Variables)
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET')
PAYPAL_API_BASE = "https://api-m.paypal.com"  # Live

def get_access_token():
        auth = (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
        headers = {'Accept': 'application/json', 'Accept-Language': 'en_US'}
        data = {'grant_type': 'client_credentials'}
        response = requests.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", auth=auth, headers=headers, data=data)
        return response.json().get('access_token')

def create_and_send_invoice(payer_email, amount, currency="USD"):
        token = get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'PayPal-Request-Id': f'inv_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        }

    # Professional Consulting Invoice Payload
        invoice_payload = {
            "detail": {
                "invoice_number": f"INV-{datetime.now().strftime('%Y%p%M%S')}",
                "reference": "Digital Mentoring Session",
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "currency_code": currency,
                "note": "Thank you for choosing our Digital Consulting services. As discussed, this session covers personalized brand strategy and mentoring.",
                "term": "This is a non-tangible digital service delivered in real-time. Non-refundable once session commences.",
                "memo": "Internal Ref: Digital_Service_Fulfillment"
            },
            "primary_recipients": [
                {
                    "billing_info": {
                        "email_address": payer_email
                    }
                }
            ],
            "items": [
                {
                    "name": "Live Digital Consulting & Mentoring Session",
                    "description": "One-on-one virtual strategy and development module.",
                    "quantity": "1",
                    "unit_amount": {
                        "currency_code": currency,
                        "value": str(amount)
                    },
                    "unit_of_measure": "QUANTITY"
                }
            ],
            "configuration": {
                "partial_payment": {
                    "allow_partial_payment": False
                },
                "allow_tip": False,
                "tax_inclusive": True
            }
        }

    # 1. Create Draft Invoice
        create_res = requests.post(f"{PAYPAL_API_BASE}/v2/invoicing/invoices", headers=headers, json=invoice_payload)
        if create_res.status_code not in [200, 201]:
                    return False, create_res.text

        invoice_id = create_res.json().get('id')

    # 2. Send Invoice (This triggers the email and receipt)
        send_res = requests.post(f"{PAYPAL_API_BASE}/v2/invoicing/invoices/{invoice_id}/send", headers=headers, json={"send_to_recipient": True})

    return send_res.status_code in [200, 201, 202, 204], send_res.text

@app.route('/webhook', methods=['POST'])
def paypal_webhook():
        data = request.json
        event_type = data.get('event_type')

    if event_type == 'PAYMENT.CAPTURE.COMPLETED':
                resource = data.get('resource', {})
                payer_email = data.get('resource', {}).get('payer', {}).get('email_address')
                amount_data = resource.get('amount', {})
                amount = amount_data.get('value')
                currency = amount_data.get('currency_code')

        if payer_email and amount:
                        success, msg = create_and_send_invoice(payer_email, amount, currency)
                        print(f"Invoice for {payer_email}: {success} - {msg}")

    return jsonify({"status": "received"}), 200

@app.route('/', methods=['GET'])
def health_check():
        return "OK", 200

if __name__ == '__main__':
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
