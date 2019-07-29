# Home Assistant Greenchoice Sensor
This is a Home Assistant custom component (sensor) that connects to the Greenchoice API to retrieve current usage data (daily meter data).

The sensor will check every hour if a new reading can be retrieved but Greenchoice practically only gives us one reading a day over this API. The reading is also delayed by 1 or 2 days (this seems to vary). The sensor will give you the date of the reading as an attribute.

### Install:
1. Place the 'greenchoice' folder in your 'custom_compontents' directory if it exists or create a new one under your config directory.
2. The Greenchoice API can theoretically have multiple contracts under one user account, so we need to figure out the ID for the contract. We will need to manually use the Greenchoice API to retrieve this using a tool like Postman.
    1. Send a POST request to https://app.greenchoice.nl/token with the following x-www-form-urlencoded body: `grant_type=password&client_id=MobileApp&client_secret=A6E60EBF73521F57&username=[youusername]&password=[yourpassword]`. You will retrieve a token.
    2. Now send a GET request to https://app.greenchoice.nl/api/v1/klant/getovereenkomsten with the token you've just retrieved in the header `"Authorization":"Bearer [yourtoken]"`. You will now get a list of all contracts (probably just one) and their IDs.
3. Add the component to your configuration.yaml, an example of a proper config entry:

```YAML
sensor:
  - platform: greenchoice
    name: meterstanden
    password: !secret greenchoicepass
    username: !secret greenchoiceuser
    overeenkomst_id: !secret greenchoicecontract
```
