import requests
from django.conf import settings

def enviar_email_brevo(to_email, subject, html_content):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "sender": {
            "name": "SmartSales365", 
            "email": "yordangallardo21@gmail.com"
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 201:
        print(f"Error al enviar email a {to_email}: {r.status_code} - {r.text}")
    return r.json()
