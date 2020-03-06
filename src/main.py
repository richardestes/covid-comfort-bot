import json
import os
from os.path import join
from ibm_watson import ToneAnalyzerV3
from ibm_watson.tone_analyzer_v3 import ToneInput
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

authenticator = IAMAuthenticator(
    'v34qLt5vjvnF1EFshCmLXFhTiwMFDgtTNpUyBbrycJFT')
service = ToneAnalyzerV3(
    version='2017-09-21',
    authenticator=authenticator)
service.set_service_url(
    'https://api.us-south.tone-analyzer.watson.cloud.ibm.com/instances/2657ddf2-a45a-4059-97b0-d04a6635b6f3')

print("\ntone() example 1:\n")
print(
    json.dumps(
        service.tone(
            tone_input='I am scared. This is a horrible day.',
            content_type="text/plain").get_result(),
        indent=2))
