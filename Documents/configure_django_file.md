
## Configure Django Files

### Step 1 Download Project (Code)
[Intelligent Reservation Project](https://github.com/KevinChngJY/IntelligentReservationSystem/tree/main/Intelligence_Reservation_Agent%20(Project-Code))

### Step 2 Configure Setting Files
Go to (Project Path)> intelligence_agent > Open setting.py,
search for ALLOWED_HOSTS, place your own ngrok link : <br>
![alt text](https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Images/configure_django1.png) 

Search for 
SOCIAL_AUTH_FACEBOOK_KEY = '1039391333163897'        # App ID
SOCIAL_AUTH_FACEBOOK_SECRET = '9341cb1fda75b7a2bb30495b9a2bb9a7'  # App Secret
Change the App ID and Secret to your own credential, refer to step 4 in [facebook authentication](https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Documents/facebook_authentication.md) for getting your app ID and Secret Key.<br>
![alt text](https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Images/configure_django2.png) 

### Step 3 Configure View Files<br>
Go to (Project Path)> nus > Open view.py,
Search for ngrok_address, put your own ngrok domain :<br>
![alt text](https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Images/configure_django3.png) 

Complete!
