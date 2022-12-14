import base64
from email.message import EmailMessage
import os.path
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


API_KEY = ""
ROOT_URL = "https://api.purpleair.com/v1/sensors"
LONG_LAT_BOUNDS = ()
AQI_THRESHOLD = 50

GMAIL_API_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
FROM_EMAIL = ""
TO_EMAIL = ""


def calculate_aqi(cp, ih, il, bph, bpl):
    """
    Helper function to calculate air quality index (AQI) given raw values.
    Uses equation from https://forum.airnowtech.org/t/the-aqi-equation.
    
    :param cp: input concentration for a given pollutant 
    :param ih: AQI value/breakpoint corresponding to bph
    :param il: AQI value/breakpoint corresponding to bpl
    :param bph: concentration breakpoint that is greater than or equal to cp
    :param bpl: concentration breakpoint that is less than or equal to cp
    :returns: AQI value
    """
    a = ih - il
    b = bph - bpl
    c = cp - bpl
    return ((a / b) * c) + il

def get_aqi_from_pm(pm, humidity):
    """
    Calculate AQI from PM2.5 and humidity values.
    First, applies US EPA's conversion on PM2.5 value via equation from
        https://cfpub.epa.gov/si/si_public_record_report.cfm?Lab=CEMM&dirEntryId=353088.
    Then, calculates AQI value via Purple Air's formula
        (https://community.purpleair.com/t/how-to-calculate-the-us-epa-pm2-5-aqi).

    :param pm: PM2.5
    :param humidity: humidity
    :returns: AQI value
    """
    # Apply US EPA conversion on pm2.5 value
    if pm >= 260:
        new_pm = 2.966 + 0.69*pm + 8.84*(10**(-4))*(pm**2)
    elif pm >= 210:
        new_pm = (0.69*(pm/50 - 21/5) + 0.786*(1 - (pm/50 - 21/5)))*pm - \
            0.0862*humidity*(1 - (pm/50 - 21/5)) + 2.966*(pm/50 - 21/5) + \
            5.75*(1 - (pm/50 - 21/5)) + 8.84*(10**(-4))*(pm**2)*(pm/50 - 21/5)
    elif pm >= 50:
        new_pm = 0.786*pm - 0.0862*humidity + 5.75
    elif pm >= 30:
        new_pm = (0.786*(pm/20 - 3/2) + 0.524*(1 - (pm/20 - 3/2)))*pm - 0.0862*humidity + 5.75
    elif pm >= 0:
        new_pm = 0.524*pm - 0.0862*humidity + 5.75
    else:
        new_pm = pm

    # Apply Purple Air's formula on their AQI calculations
    if new_pm is None or new_pm > 1000:
        return "-"
    if new_pm < 0:
        return new_pm
    # hazardous
    if new_pm > 350.5:
        return calculate_aqi(new_pm, 500, 401, 500.4, 350.5)
    # hazardous
    elif new_pm > 250.5:
        return calculate_aqi(new_pm, 400, 301, 350.4, 250.5)
    # very unhealthy
    elif new_pm > 150.5:
        return calculate_aqi(new_pm, 300, 201, 250.4, 150.5)
    # unhealthy
    elif new_pm > 55.5:
        return calculate_aqi(new_pm, 200, 151, 150.4, 55.5)
    # unhealthy for sensitive groups
    elif new_pm > 35.5:
        return calculate_aqi(new_pm, 150, 101, 55.4, 35.5)
    # moderate
    elif new_pm > 12.1:
        return calculate_aqi(new_pm, 100, 51, 35.4, 12.1)
    # good
    elif new_pm >= 0:
        return calculate_aqi(new_pm, 50, 0, 12, 0)
    else:
        return None

def generate_request_url(lng_lat_bounds):
    """
    Generate request URL.
    
    :param sensor_idx_arr: list of sensor indices
    :returns: request URL for Purple Air API
    """
    ret_url = ROOT_URL

    # attach API key
    ret_url += "?api_key=" + API_KEY

    # grab raw pm2.5 data real time
    ret_url += "&fields=name,pm2.5_atm,humidity"

    # filter for relevant sensors via longitude/latitude bounds
    ret_url += "&nwlng=" + str(lng_lat_bounds[0])
    ret_url += "&nwlat=" + str(lng_lat_bounds[1])
    ret_url += "&selng=" + str(lng_lat_bounds[2])
    ret_url += "&selat=" + str(lng_lat_bounds[3])

    return ret_url


def filter_aqi(all_aqi):
    """
    Filter out sensors where AQI value is <= AQI_THRESHOLD.

    :param all_aqi: dict of sensor names mapped to AQI values
    :returns: dict of sensor names mapped to AQI values
    """
    impt_aqi = {}

    for k, v in all_aqi.items():
        if v > AQI_THRESHOLD:
            impt_aqi[k] = v

    return impt_aqi

def send_alert(impt_aqi):
    """
    Send alert regarding sensors where AQI > AQI_THRESHOLD.

    :param impt_aqi: dict of sensor names mapped to AQI values
    :returns: message object, including message ID
    """
    # construct email message
    send_msg = "There are high AQI levels detected near you: \n"
    for k,v in impt_aqi.items():
        send_msg += "Sensor <" + k + ">: " + str(v) + "\n"

    # authenticate with Gmail API
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GMAIL_API_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", GMAIL_API_SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # send email
    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        message.set_content(send_msg)

        message["To"] = TO_EMAIL
        message["From"] = FROM_EMAIL
        message["Subject"] = "PurpleAir Alerts - High AQI Detected"

        # encode message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()) \
            .decode()

        create_message = {
            "raw": encoded_message
        }
        # pylint: disable=E1101
        send_message = (service.users().messages().send
                        (userId="me", body=create_message).execute())
        print(F'Message Id: {send_message["id"]}')

    except HttpError as error:
        print(F'An error occurred: {error}')
        send_message = None

    return send_message


def main():
    """
    Main function.
    """
    req_url = generate_request_url(LONG_LAT_BOUNDS)
    response = requests.get(req_url)

    # got expected response
    if response.status_code == 200:
        content_data = response.json()["data"]
        
        # calculate aqi values
        all_aqi = {}
        for sensor_data in content_data:
            all_aqi[sensor_data[1]] = get_aqi_from_pm(sensor_data[3], sensor_data[2])

        print("all aqi: " + str(all_aqi))

        # determine if aqi values should be alerted on
        alerts = filter_aqi(all_aqi)
        if len(alerts) > 0:
            send_alert(alerts)

    else:
        print("Error in main: Got a(n) {response.status_code} error response.")


main()