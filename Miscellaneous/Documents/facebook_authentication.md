## FACEBOOK AUTHENTICATION


### Step 1 : Sign up and login into facebook developer <br>
https://developers.facebook.com/ <br>
  
### Step 2 : Create New Apps <br>
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/facebook1.png" width="700" /> <br>
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/Facebook2.png" width="700" /> <br>

### Step 3 : Configure the Created App <br>
Go to Settings>Basic, <br>
In the column of "App Domain", type localhost and your own ngrok domain as follows: <br>
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/facebook3.png" width="700" /> <br><br>

In the column of "Private Policy URL", paste the link below into the column: <br>
https://www.privacypolicies.com/live/d668e0b2-59f2-44fe-9881-183cbe216be9 <br>
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/facebook4.png" width="700" /> <br><br>
(You may generate your own privacy policies)

Scroll down until you see the section of "Website", paste the link below into the column: <br>
http://localhost:8000/
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/facebook5.png" width="700" /> <br><br>

Save the changes!

Go to Products>Facebook Login>Setting, <br>
in the column of "Valid OAuth Redirect URIs", paste the 3 links below into the column : <br>
https://(your own ngrok link)/intelligentreservationagent/login/ <br>
https://(your own ngrok link)/intelligentreservationagent/social-auth/complete/facebook <br>
https://(your own ngrok link)/intelligentreservationagent/home/ <br>
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/facebook6.png" width="700" /> <br><br> 

### Step 4 : Complete! Now copy your App ID and App Secret<br>
(It is required for django backend system, the documentation will remind you again when it requires you to configure django's setting)<br>
Go to Settings>Basic, <br>
<img src="https://github.com/KevinChngJY/IntelligentReservationSystem/blob/main/Miscellaneous/Images/facebook7.png" width="700" /> <br><br> 
