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

def get_aqi_from_pm(pm):
    # https://community.purpleair.com/t/how-to-calculate-the-us-epa-pm2-5-aqi

    if pm is None or pm > 1000:
        return "-"
    if pm < 0:
        return pm

    # hazardous
    if pm > 350.5:
        return calculate_aqi(pm, 500, 401, 500.4, 350.5)
    # hazardous
    elif pm > 250.5:
        return calculate_aqi(pm, 400, 301, 350.4, 250.5)
    # very unhealthy
    elif pm > 150.5:
        return calculate_aqi(pm, 300, 201, 250.4, 150.5)
    # unhealthy
    elif pm > 55.5:
        return calculate_aqi(pm, 200, 151, 150.4, 55.5)
    # unhealthy for sensitive groups
    elif pm > 35.5:
        return calculate_aqi(pm, 150, 101, 55.4, 35.5)
    # moderate
    elif pm > 12.1:
        return calculate_aqi(pm, 100, 51, 35.4, 12.1)
    # good
    elif pm >= 0:
        return calculate_aqi(pm, 50, 0, 12, 0)
    else:
        return None


def get_sensor_indices():
    return TEMP_SENSOR_IDXS

def generate_request_url(sensor_idx_arr):
    ret_url = ROOT_URL

    # attach API key
    ret_url += "?api_key=" + API_KEY

    # grab raw pm2.5 data real time
    ret_url += "&fields=pm2.5_cf_1"

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
            all_aqi[sensor_data[0]] = get_aqi_from_pm(sensor_data[1])

        print("all aqi: " + str(all_aqi))

        # determine if aqi values should be alerted on
        alerts = filter_aqi(all_aqi)
        if len(alerts) > 0:
            send_alert(alerts)

    else:
        print("Error in main: Got a(n) {response.status_code} error response.")

main()