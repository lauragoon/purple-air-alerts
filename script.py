import requests

ROOT_URL = "https://api.purpleair.com/v1/sensors"
TEMP_SENSOR_IDXS = []
API_KEY = ""


def calculate_aqi(cp, ih, il, bph, bpl):
    # https://forum.airnowtech.org/t/the-aqi-equation

    a = ih - il
    b = bph - bpl
    c = cp - bpl
    return ((a / b) * c) + il

def get_aqi_from_pm(pm, humidity):
    # https://cfpub.epa.gov/si/si_public_record_report.cfm?Lab=CEMM&dirEntryId=353088
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

    # https://community.purpleair.com/t/how-to-calculate-the-us-epa-pm2-5-aqi
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


def get_sensor_indices():
    return TEMP_SENSOR_IDXS

def generate_request_url(sensor_idx_arr):
    ret_url = ROOT_URL

    # attach API key
    ret_url += "?api_key=" + API_KEY

    # grab raw pm2.5 data real time
    ret_url += "&fields=name,pm2.5_atm,humidity"

    # filter for relevant sensors
    ret_url += "&show_only="
    for i in range(len(sensor_idx_arr)):
        if i != 0:
            ret_url += "%2C"
        ret_url += str(sensor_idx_arr[i])

    return ret_url


def filter_aqi(all_aqi):
    impt_aqi = {}

    for k, v in all_aqi.items():
        if v > 50:
            impt_aqi[k] = v

    return impt_aqi

def send_alert(impt_aqi):
    print("Test send alert: " + str(impt_aqi))


def main():
    sensors = get_sensor_indices()
    
    req_url = generate_request_url(sensors)
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