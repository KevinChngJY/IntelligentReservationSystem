import os
import dialogflow_v2beta1 as da
from google.api_core.exceptions import InvalidArgument
import pandas as pd
from pathlib import Path
import sqlite3
import datetime
from dateutil.parser import *
#variables used for communication


acknowledgement=True
suggestion_list=[]
availability=True
initial_info={}
suggestion_from_rules=()

def fetch_from_db(queree):
    try:
         conn=sqlite3.connect(os.path.join(Path(__file__).resolve(strict=True).parent.parent, 'db.sqlite3'))
         df = pd.read_sql_query(queree, conn)
         return df
    except conn.Error as e:
        print('The error is: ',e)
    return 

# method to fetch userid, username , establishment id from db
def load_userinfo_from_table():
    user_info=fetch_from_db("SELECT id,user_id,user_address,user_country,user_city, user_postal FROM nus_users_name")
    return user_info
# method to fetch establishment names from db
def load_establishment_from_table():
    #establishment_list=['AK', 'Cedelee','Starbuck','CoffeeBean','SoupeSpoon']
    establishment=fetch_from_db("SELECT company,location, username FROM nus_establishments WHERE type_business='Restaurant'")
    
    return establishment

# method to fetch clinic establishment names from db
def load_c_establishment_from_table():
    establishment=fetch_from_db("SELECT company,location, username FROM nus_establishments WHERE type_business='Clinic'")
    return establishment

# method to fetch shop establishment names from db
def load_s_establishment_from_table():
    establishment=fetch_from_db("SELECT company,location, username FROM nus_establishments WHERE type_business='Shop'")
    return establishment

# method to fetch establishment names from db
def load_r_establishment_from_table(etype):
    #establishment_list=['AK', 'Cedelee','Starbuck','CoffeeBean','SoupeSpoon']
    if etype=='restaurant':
        establishment=load_establishment_from_table()
    elif etype=='clinic':
        establishment=load_c_establishment_from_table()
    elif etype=='shop':
        establishment=load_s_establishment_from_table()
    ecomp_loc=[]
    e1=establishment['company']
    l=len(e1)
    e2=establishment['location']
    for i in range(l):
        ecomp_loc+= [e1[i]+' @ '+e2[i]]
    return ecomp_loc


# method to fetch establishment id from db
def load_ruid_establishment_from_table(etype):
    if etype=='restaurant':
        establishment=load_establishment_from_table()
    elif etype=='clinic':
        establishment=load_c_establishment_from_table()
    elif etype=='shop':
        establishment=load_s_establishment_from_table()
    ecomp_uid=[]
    e1=establishment['company']
    l=len(e1)
    e3=establishment['username']
   
    for i in range(l):
        ecomp_uid+= [e1[i]+' @ '+e3[i]]
    return ecomp_uid



def load_euniqueId_from_table(name, etype):
      name=name.split(' @ ')
      company=name[0]
      location=name[1]
      euid=fetch_from_db("SELECT username FROM nus_establishments WHERE company like ? and location like ? and type_business like ?",(company,location,etype))
      print(euid)
     
      return euid

#method to fetch establishment names from table
def post_establishment_entity_to_bot():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'ira-lmam-e04216b7b1c6.json'
    
    client=da.EntityTypesClient()
    parent = client.project_agent_path('ira-lmam')
    
    establishment_list=load_r_establishment_from_table('restaurant')
    print(establishment_list)
         
    for i in establishment_list:
       entity_to_add = da.types.EntityType.Entity(
        value = i,
        synonyms = [i]
        )
        
       response = client.batch_create_entities('projects/ira-lmam/agent/entityTypes/aa156388-d264-424d-9746-a7452962831b', [entity_to_add])

#method to fetch clinic establishment names from table
def post_c_establishment_entity_to_bot():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'ira-lmam-e04216b7b1c6.json'
    
    client=da.EntityTypesClient()
    parent = client.project_agent_path('ira-lmam')
    
    establishment_list=load_r_establishment_from_table('clinic')
    print(establishment_list)
         
    for i in establishment_list:
       entity_to_add = da.types.EntityType.Entity(
        value = i,
        synonyms = [i]
        )
        
       response = client.batch_create_entities('projects/ira-lmam/agent/entityTypes/fdd37879-f082-4a83-a18b-a0193b727da1', [entity_to_add])

#method to fetch clinic establishment names from table
def post_s_establishment_entity_to_bot():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'ira-lmam-e04216b7b1c6.json'
    
    client=da.EntityTypesClient()
    parent = client.project_agent_path('ira-lmam')
    
    establishment_list=load_r_establishment_from_table('shop')
    print(establishment_list)
         
    for i in establishment_list:
       entity_to_add = da.types.EntityType.Entity(
        value = i,
        synonyms = [i]
        )
        
       response = client.batch_create_entities('projects/ira-lmam/agent/entityTypes/6ed52b33-93dc-4b6f-9624-2188705058b9', [entity_to_add])

def load_upcoming_table(entity):
    conn=sqlite3.connect(os.path.join(Path(__file__).resolve(strict=True).parent.parent, 'db.sqlite3'))
    db = conn.cursor()
   
    db.execute("SELECT e.company,n.n_person,n.time_in,n.status FROM nus_reservations n  INNER JOIN nus_establishments e on e.username=n.establishment where n.status!='cancelled' and n.status!='changed' and n.patron=?;",(entity,))
   
    data=[]
    data=db.fetchall()
    print('data from distinct: ',data)
    return data


def process_date_to_rules(selected_slot):
    selection=datetime.datetime.strptime(selected_slot, '%A %d %B %Y at %H:%M:%S') 
    selection=datetime.datetime.strftime(selection, '%y/%m/%d_%H:%M')
    return selection
def process_date1_to_rules(selected_slot):
    selection=datetime.datetime.strptime(selected_slot, '%A %d %B %Y at %H:%M') 
    selection=datetime.datetime.strftime(selection, '%y/%m/%d_%H:%M')
    return selection

def process_timeOut(m2):
    # m2=m2.lower()
    # c=0
    # if 'pm' in m2:
    #     m2=m2.replace('pm','')
        
    # elif 'am' in m2:
    #     m2=m2.replace('am','')
    # m2=m2.strip()
    # print(m2)
    m2=m2.replace('.',':')
    
    m2=parse(m2)
    print(m2)
    to=datetime.datetime.strftime(m2, '%H.%M')
    return to


# method to fetch establishment names from db
def load_company_details_from_table(entity):
    #establishment_list=['AK', 'Cedelee','Starbuck','CoffeeBean','SoupeSpoon']
    conn=sqlite3.connect(os.path.join(Path(__file__).resolve(strict=True).parent.parent, 'db.sqlite3'))
    db = conn.cursor()
    
    db.execute("select company,location,contact, max_cap, open_days, open_time, close_time from nus_establishments where username =?;",(entity,))
   
    data=db.fetchall()
    # print(data)
    return data

# method to fetch reservations from db
def load_reservation_details_from_table(Patron):
    #establishment_list=['AK', 'Cedelee','Starbuck','CoffeeBean','SoupeSpoon']
    conn=sqlite3.connect(os.path.join(Path(__file__).resolve(strict=True).parent.parent, 'db.sqlite3'))
    db = conn.cursor()
    
    db.execute("SELECT establishment,n_person,time_in,time_out,status FROM nus_reservations where patron =?;",(Patron,))
   
    data=db.fetchall()
    # print(data)
    return data

def Convert(tup, di): 
    for a, b in tup: 
        di.setdefault(a, []).append(b) 
    return di

# method to check with rules on reservation of slot
def book_slot_to_rules(book_reservation_intentInfo):
    
    return suggestion_from_rules

def process_suggestion1(suggestion_from_rules):
    suggestion_list=suggestion_from_rules.split('available time:')
    del suggestion_list[0]
    suggestion_list=suggestion_list[0].split(',')
    return suggestion_list

def process_suggestion(msg):
    import re
    k=re.split(r'[()]\s*',msg)
    k.remove(k[0])
    k.remove(k[0])
    k.remove(k[0])
    j=[]
    a=0
    start=1
    end=len(k)+1
    for i in range(start, end+1):
        if (i<10) and (i%2!=0):
            j+=[k[i]]
            m=[]
            for i in j:
                m.append(i.strip())
                print(m)
    suggestion_list=m
    return suggestion_list

def process_suggestion2(msg):
    import re

    k=msg.split('Please choose from the upcoming reservation slot(s):')
    print(k[1])
    b=k[1]
    k=re.split(r'[()]\s*',b)
    print(k)
    k.remove(k[0])
    k.remove(k[0])
    print(k)
    j=[]
    a=0
    start=0
    end=len(k)+1
    for i in range(start, end):
        print(i)
        if (i<10) and (i%2==0):
            j+=[k[i]]
            print(j)
    m=[]
    for i in j:
        m.append(i.strip())
    print(m)
    suggestion_list=m
    return suggestion_list

def process_suggestion3(msg):
    import re

    k=msg.split('Available time slot(s):')
    print(k[1])
    b=k[1]
    k=re.split(r'[()]\s*',b)
    print(k)
    k.remove(k[0])
    k.remove(k[0])
    print(k)
    j=[]
    a=0
    start=0
    end=len(k)+1
    for i in range(start, end):
        print(i)
        if (i<10) and (i%2==0):
            j+=[k[i]]
            print(j)
    m=[]
    for i in j:
        m.append(i.strip())
    print(m)
    suggestion_list=m
    return suggestion_list

def process_session(e):
    e=e.split('dfMessenger-')
    print(e)
    f=e[1]
    print(f)
    return f


# method to check with rules on cancellation of slot
def cancel_slot_to_rules(cancel_reservation_intentInfo):
    
    
    return acknowledgement, suggestion_list


# method to check with rules on change of slot by date
def change_slot_by_date(changeBydate_intentInfo):
    
    return availability, suggestion_list

# method to check with rules on change of slot by reduce seats
def change_slot_by_seat_minus(reduceSeats_intentInfo):
    
    return acknowledgement, suggestion_list

# method to check with rules on change of slot by add seats
def change_by_slot_add_seats(addMoreseats_intentInfo):
    
    return availability, suggestion_list
    