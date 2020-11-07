
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
> `Agent` class handles all interactions with rules.
> `HouseKeeping` class handles maintenance of resources (e.g. database entries)

Configuration file **config.ini** has link to database (and its tables) as well as rules builder. 
It may be modified to: 
1. Configure custom rules or rules order, and
2. Path to link to different database. 

In addition, there is **util.py** that is useful for initialization and simulation.

A. Initialization

In addition to **ira.py** module and configuratio file **config.ini**, there must be a database file. 
To generate database file run code below: 
>`import util`
>`util.init_db()`
This generates **dummy.db** database file, and six tables associated to rules engine. 
Default database and table names may be overridden. 

---
## SECTION 6 : PROJECT REPORT / PAPER

#### Django Workflow (Backend) :

#### Registration/Reservation (Frontend) :

#### Diaglog flow (Chatbot) :

#### Rule-based Engine / GA (Algorithm) :

---
