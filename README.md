# PurpleAir Alerts
Get alerts when your nearest PurpleAir sensor(s) reachers a certain air quality index (AQI) threshold.

## How to run this
1. Setup access to the [PurpleAir](https://api.purpleair.com) and [Gmail](https://developers.google.com/gmail/api) APIs.
2. Replace `API_KEY` with your PurpleAir API key.
3. Replace `LAT_LONG_BOUNDS` with a 4-tuple that consists of: (north west longitude, north west latitude, south east longitude, and south east latitude). These will bound the geographic area where sensor data will be taken from.
4. Replace `TO_EMAIL` and `FROM_EMAIL` fields with your desired email addresses.
5. Run the script. (The first time you run it, you'll need to go through an auth flow with Gmail)
   - In order to run this continuously, you will need to hook this up to an external service.
   
## How this works
1. Connects to PurpleAir API and grabs relevant sensors based on user-input longitude/latitude bounds.
2. Modifies PM2.5 values received from these sensors with a [USA EPA conversion formula](https://cfpub.epa.gov/si/si_public_record_report.cfm?Lab=CEMM&dirEntryId=353088).
3. [Converts](https://community.purpleair.com/t/how-to-calculate-the-us-epa-pm2-5-aqi) these values to AQI values.
4. Determines which sensors show AQI values > 50.
5. Send an email about these sensors via the Gmail API.

## Dependencies
- PurpleAir API
- Gmail API
- Libraries listed in dependencies.txt
