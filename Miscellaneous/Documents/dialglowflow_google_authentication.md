## Dialogflow – Google Authentication

In Dialogflow's console, go to settings and under the general tab, you'll see the project ID section with a Google Cloud link to open the Google Cloud console. Open Google Cloud.
In the Cloud console, go to the menu icon ☰ > APIs & Services > Credentials
Under the menu icon ☰ > APIs & Services > Credentials > Create Credentials > Service Account Key.
Under Create service account key, select New Service Account from the dropdown and enter. If you already have a service account key, select that.
Name it as IRA and click Create. In the popup, select Create Without Role.
JSON file will be downloaded to your computer that you will need in the setup sections below.
Set up Dialogflow DetectIntent endpoint to be called from the App
Inside nus folder, place the ira--xxxx.json file.
In settings.py in intelligent_agent folder, include
 LOAD_JSON = {
    'DATA_DIRS': [os.path.join(BASE_DIR, 'ira-lmam-e04216b7b1c6')],
}

This json authentication file enables updating the entity values in dialogflow from the app.

##### Dialogflow – To enable webhook
In Dialogflow, select fulfilments and enable, webhook as 
![alt text](https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Images/webhook.png) 
