import json
import requests
from flask import Flask, render_template, request, session
import secrets
import time

app = Flask(__name__)

# Generate a random secret key of 32 bytes (256 bits)
random_secret_key = secrets.token_hex(32)

# keys_defining
app.secret_key = random_secret_key
api_key = "bGJlcWlyaUB0ZWxxdWVzdGludGwuY29tOkkoTSpjYTY5cEBvKS1FeTAjeHtEKFNVJ2NmYzVpeQ==  "





@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')


@app.route('/submit', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Your authentication process here (replace with your actual process)
        authentication_url = "https://api-services.uat.1placedessaisons.com/uatm/v1/idp/oauth2/authorize"
        payload = json.dumps({"apiKey": api_key})
        headers = {'Content-Type': 'application/json', 'Authorization': '1'}
        response = requests.request("POST",
                            authentication_url,
                            headers=headers,
                            data=payload)
        authentication_token_response = response.json()
        
        #Store Authentication Token in a variable
        authentication_token = authentication_token_response['access_token']
        

        # Second API Call - Search for Company
        search_company_url = "https://api-services.uat.1placedessaisons.com/search/uatm-v2/companies/matching"
        session['token'] = 'Bearer ' + authentication_token
        token = session.get('token')
        headers = {'Content-Type': 'application/json', 'Authorization': token}
        payload = json.dumps({
            "requestedSize": 2,
            "companyName": request.form['companyName'],
            "streetName": request.form['streetName'],
            "companyIdentifierTypeCode": "EH",
            "streetNumber": request.form['streetNumber'],
            "town": request.form['town'],
            "postalCode": request.form['postalCode'],
            "countryCode": request.form['countryCode']
        })
        response = requests.request("POST",
                            search_company_url,
                            headers=headers,
                            data=payload)        
        response_json = response.json()
        data = response_json["results"][0]['company']
        
        communication_channels = data.get("communicationChannels", [])
        phone_numbers = [channel["value"] for channel in communication_channels if channel["typeCode"] == "PHONE_NUMBER"]
        website = next((channel["value"] for channel in communication_channels if channel["typeCode"] == "WEBSITE"), None)
        address = data.get("address", {})

        
        session['company_id'] = response_json["results"][0]['company']['companyId']
        company_name = response_json["results"][0]['company']['legalData']['companyName']
       
    return render_template('amount.html', company_id=session.get('company_id'), company_name=company_name,address=address, phone_numbers=phone_numbers, website=website)


#4th API CALL Function
def search_jobid(JobId, token):
    
    search_job_url = 'https://api-services.uat.1placedessaisons.com/uatm/riskinfo/v3/jobs/' + str(JobId)
    payload = {}
    headers  = {'Content-Type': 'application/json', 'Authorization': token}
    time.sleep(50)
    response = requests.request("GET",
                                search_job_url,
                                headers=headers,
                                data=payload)
    response_json = response.json()
    return response_json



@app.route('/amount', methods=['GET', 'POST'])
def cover_request():
    if request.method == 'POST':
        requested_amount = request.form['amount']
        cover_request_url = "https://api-services.uat.1placedessaisons.com/uatm/riskinfo/v3/covers"
        token = session.get('token')

        payload = json.dumps({
                    "requestTypeCode": "Primary",
                    "policy": {
                        "businessUnitCode": "ACI",
                        "policyId": "5121840"
                    },
                    "creditLimitDetails": {
                        "requestedAmount": requested_amount,
                        "currencyCode": "USD"
                    },
                    "companyId": session.get('company_id'),
                    "isRequestUrgent": True
                    })

        headers = {'Content-Type': 'application/json', 'Authorization': token}

        response = requests.request("POST",
                                    cover_request_url,
                                    headers=headers,
                                    data=payload)
    JobId = response.json()

    #4th API CALL - Search JobId
    response_json = search_jobid(JobId, token)
    try:
        resource_url = response_json["resourceUrl"]
    except:
        return 'jobStatusCode : {}'.format(response_json["jobStatusCode"])


    # #5th API call
    cover_search_url = resource_url
    payload = {}
    response = requests.request("GET",
                                cover_search_url,
                                headers=headers,
                                data=payload)
    response_json = response.json()
    Decision = response_json['creditLimitsAggregation']['creditLimits'][0]['technicalDecisionStatusCode']
    
    amount = response_json['creditLimitsAggregation']['creditLimits'][0]['amount']

    start_date = response_json['creditLimitsAggregation']['creditLimits'][0]['startDate']

    if Decision == 'AlreadyAgreed':
        result = f"You have been approved for the amount of ${amount}\n"
        result += "Final Request Decision: Approved\n"
        result += f"Amount: ${amount}\n"
        result += f"Start Date: {start_date}"
    else:
        result = "Your request was not approved."

    return result




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
