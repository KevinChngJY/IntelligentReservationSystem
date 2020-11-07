
---

## SECTION 1 : PROJECT TITLE
## Intelligent Reservation System

<img src="Title2.jpg"
     style="float: left; margin-right: 0px;" />

---
## SECTION 2 : EXECUTIVE SUMMARY / PAPER ABSTRACT


---
## SECTION 3 : CREDITS / PROJECT CONTRIBUTION

| Official Full Name  | Student Id | Work Items (Who Did What) | Email (Optional) |
| :------------ |:----------------| :-----|:----------------|
| Januwar Hadi |  |Rule-based Engine, GA, Database Design |  |
| Rajamanickam Hamsamalini |  |Chatbot,Django-Chatbot Integration, Database Design | |
| Kevin Chng Jun Yan |   |Django Backend, Frontend, Database Design | kevinchng@hotmail.com |

---
## SECTION 4 : VIDEO OF SYSTEM MODELLING & USE CASE DEMO

[![INTELLIGENT EMPLOYEE SCHEDULER]()

---
## SECTION 5 : USER GUIDE


### To run the system in local machine
#### Ngrok Activation : [a link](https://github.com/user/repo/blob/branch/ngrok.md)

#### Facebook Authentication

#### Google Map Platform Authentication

#### Diaglogflow Authentication

#### Rules Engine

Rules and its attribute classes are contained in **ira.py**. 
Two classes that may be used are: 
1.  `Agent` class that handles all interactions with rules.
2.  `HouseKeeping` class that handles maintenance of resources (e.g. database entries)

Configuration file **config.ini** has link to database (and its tables) as well as rules builder. As a text file, It may be modified to: 
1. Configure custom rules or rules order, and
2. Path to link to different database. 

In addition, there is **util.py** that is useful for initialization and simulation.

A. Initialization

In addition to **ira.py** module and configuratio file **config.ini**, there must be a database file. 
To generate database file run code below: 
`import util`
`util.init_db()`
This generates **dummy.db** database file, and six tables associated to rules engine.  
This also generates dummy patrons (default is 100 patrons) and establishments (default 5). 
Default database, table names and number of entries may be overridden.

To create simulated data, run code below from **util.py** module. 
Do take note that the database configuration must match **config.ini** file. 
'util.create_dummy_appointments()'
This will populate *query* and *reservation* tables with random entries up to 3 days. 


---
## SECTION 6 : PROJECT REPORT / PAPER

#### Django Workflow (Backend) :

#### Registration/Reservation (Frontend) :

#### Diaglog flow (Chatbot) :

#### Rule-based Engine / GA (Algorithm) :

---
