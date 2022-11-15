# PurpleAir Alerts
Get alerts when your nearest PurpleAir sensor(s) reachers a certain air quality index (AQI) threshold.

## How it works
Currently...
- Grabs relevant sensors based on user-input longitude/latitude bounds.
- Modifies PM2.5 values from PurpleAir API via USA EPA conversion.
- Converts this value to AQI value.
- Determines which sensors show AQI values > 50.
- (WIP to send alerts).

## Dependencies
- PurpleAir API key
