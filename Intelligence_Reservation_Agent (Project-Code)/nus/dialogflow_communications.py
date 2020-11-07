# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 14:42:16 2020

@author: Hamsi
"""


# from .models import users_name, business_register, establishment_register, user_reservation, user_notification,establishments

import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from logging import DEBUG, getLogger
from typing import Dict
import datetime
import pandas as pd
import pytz
import dateutil.parser as parser
import calendar
from . import communications_channel as comm
from . import ira

 # Create logger and enable info level logging
 
logger = getLogger(__name__)
logger.setLevel(DEBUG)

# Dictionaries for intents
global msg, countOfestablishment, session_company, flow
countOfestablishment=0

flow={}
est_list={}
establishment_info={}
book_reservation_intentInfo={}
cancel_reservation_intentInfo={}
changeBydate_intentInfo={}
check_reservation_intentInfo={}
addMoreseats_intentInfo={}
reduceSeats_intentInfo={}
acknowledgement='Yes'
scode=0
msg=(
 'available time: Thursday 15 October 2020 at 11:00, Thursday 15 October 2020 at 10:40, Thursday 15 October 2020 at 11:20, Wednesday 14 October 2020 at 11:00, Friday 16 October 2020 at 11:00 ')




#Function: convert isoformat time to string
def isoformatTimetoString(timeStart):
    d=parser.parse(timeStart)
    ts=d.strftime('%H:%M:%S')
    return ts

#Function: convert isoformat date to string

def isodateToString(date_of_reservation):
    date_of_reservation=parser.parse(date_of_reservation)
    date_of_reservation=date_of_reservation.strftime('%m/%d/%y %H:%M:%S')
    date_of_reservation=datetime.datetime.strptime(date_of_reservation,'%m/%d/%y %H:%M:%S')
    d=date_of_reservation.weekday()
    w=calendar.day_name[d]
    m=date_of_reservation.month
    m=calendar.month_name[m]
    y=date_of_reservation.year
    date_of_reservation_txt=w+' '+str(date_of_reservation.day)+' ' +m+' '+str(y) 
    return date_of_reservation_txt,date_of_reservation


def input_welcome(req,patron,name):
    # welcome_intentInfo=process_patroninfo(patron)
    response_text='Hi '+name+' ! IRA welcomes you!  '
    
    data=comm.load_upcoming_table(patron)
    print(data)
    b=[]
    tag=''
    z=len(data)
    if z>3: 
        z=3
    if z>0 and z<4:
        response_text+='\n Your upcoming reservation status...\n '+'-'*45+'\n'
        for i in range(z):
            b=list(data[i])
            for i in range(len(b)):
                if i==0:
                    tag='\nEstablishment: '
                elif i==1:
                    tag='No. of Person(s) :'
                elif i==2:
                    tag='Time in :'
                    b[i]=datetime.datetime.strptime(b[i],'%y/%m/%d_%H:%M')
                    b[i]=datetime.datetime.strftime(b[i],'%y/%m/%d at %H:%M')
                elif i==3:
                    tag='Status :'
                response_text+=tag+b[i]+'\n '
        response_text+='\n'
    elif z==0:
        response_text+='\n'+'-'*45+'\nTo do reservation ....'
    response_text+='\nKey [m] to Main menu...'
    fulfillmentText = {'fulfillmentText': response_text} 
    return fulfillmentText
    


#Function: process to select establishment request

def establishment_list(req,patron,e_type):
    flow['intent']='establishment_list'
    flow['etype']=e_type
    intent_name=req['queryResult']['action'] #intent name
    session_info=req['session'] #intent session
    est_list=comm.load_r_establishment_from_table(e_type)
    
    print(est_list)
    establishment_info['type']=e_type
    response_text='Listing '+e_type+' \n '+'-'*50+'\n'
    count=1
    for i in est_list:
        response_text+=str(count)+'.   '+i+' \n'
        count+=1
    print(e_type)
    countOfestablishment=count
    flow['elist']=est_list
    response_text+='\n Key in option number : \n'
    fulfillmentText = {'fulfillmentText': response_text} 
    # print(establishment_info)
    # print(req['queryResult']['parameters'])
    # print(establishments.objects.values_list('company', flat=True))
    return fulfillmentText

def process_establishmentname(op, etype):
    op=int(op)
    print(op)
    el=comm.load_r_establishment_from_table(etype)
    return el[op-1]

def process_establishmentuid(op, etype):
    print(op,type(op))
    op=int(op)
    eu=comm.load_ruid_establishment_from_table(etype)
    uid=eu[op-1]
    uid=uid.split(' @ ')
    return uid[1]

#Function: process to book a reservation request

def book_a_reservation(req, Patron,name):
     flow['intent']='book_a_reservation'
    #Fetch intent info
     #print('from book', establishment_info)
     print('b1 parameters: ',req['queryResult']['parameters'])
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='NewReservation'
     session_info=req['session'] #intent session
     session_info=comm.process_session(session_info)
     print(session_info)
    
     choice=req['queryResult']['parameters']['option']
     choice=int(choice)
     print('from br: ',flow['elist'])
     print('from br: ',flow['elist'][choice-1])
     establishment=flow['elist'][choice-1]
     #establishment=process_establishmentname(req['queryResult']['parameters']['option'],establishment_info['type'])#Restaurant name
     uid=process_establishmentuid(req['queryResult']['parameters']['option'],establishment_info['type'])
     timeStart=req['queryResult']['parameters']['timeStart'] #slot begin time
     timeOut=req['queryResult']['parameters']['timeOut'] #slot end time
     ts=isoformatTimetoString(timeStart)
     if timeOut!='0':
         timeOut=comm.process_timeOut(timeOut)
     #print('ts: ',ts)
    
     no_of_seats=int(req['queryResult']['parameters']['seats']) # No of seats
     date_of_reservation=req['queryResult']['parameters']['day'] # date_of_reservation
     date_of_reservation_txt,dor=isodateToString(date_of_reservation)
     today=datetime.datetime.today()
     response_text=''
     countOfestablishment=len(comm.load_r_establishment_from_table(establishment_info['type']))
     print(date_of_reservation_txt,dor)
     ts=datetime.datetime.strptime(ts, '%H:%M:%S')
     ts=datetime.datetime.strftime(ts, '%H:%M')
     d=datetime.datetime.strftime(dor, '%y/%m/%d')
     
     time_in=str(d)+'_'+str(ts)
     time_in=datetime.datetime.strptime(time_in,'%y/%m/%d_%H:%M')
     time_in=datetime.datetime.strftime(time_in,'%y/%m/%d_%H:%M')
     print(time_in,timeOut)
         
     if (int(req['queryResult']['parameters']['option'])>countOfestablishment):
         response_text='No such establishment.'
         fulfillmentText = {'fulfillmentText': response_text}
     elif str(timeOut)!='0':
        if len(timeOut)<=2:
            to=datetime.datetime.strptime(timeOut, '%H')
        elif '.' in timeOut:
            to=datetime.datetime.strptime(timeOut, '%H.%M')
        elif ':' in timeOut:
            to=datetime.datetime.strptime(timeOut, '%H:%M')
        
        to=datetime.datetime.strftime(to, '%H:%M')
        timeout=str(d)+'_'+str(to)
        time_out=datetime.datetime.strptime(timeout,'%y/%m/%d_%H:%M')
        time_out=datetime.datetime.strftime(time_out,'%y/%m/%d_%H:%M')
        book_reservation_intentInfo['timeout']=time_out
        
        response_text='%s says : You have requested for a reservation on %s from %s to %s for %d people....'%(establishment,date_of_reservation_txt,ts,to,no_of_seats)
        response_text+= '\n Key [c] to confirm ....\n Key [m] to Main menu ....'
        fulfillmentText = {'fulfillmentText': response_text}
     #If all validations apply the rule
     else:
         book_reservation_intentInfo['timeout']='0'
         response_text='%s says : You have requested for a reservation on %s from %s for %d people.'%(establishment,date_of_reservation_txt,ts,no_of_seats)
         response_text+='\n\n'+'-'*45
         response_text+= '\n Key [c] to confirm ....\n Key [m] to Main menu ....'
         fulfillmentText = {'fulfillmentText': response_text} 
    
     #Set the book_reservation_intentInfo dictionary
     book_reservation_intentInfo['userId']=Patron
     book_reservation_intentInfo['businessId']=str(uid)
     
     book_reservation_intentInfo['session']=str(session_info)
     book_reservation_intentInfo['timeStart']=timeStart
     book_reservation_intentInfo['No_of_Seats']=str(no_of_seats)
     book_reservation_intentInfo['date_of_reservation']=date_of_reservation
     
     book_reservation_intentInfo['fromIntent']=intent_name
     book_reservation_intentInfo['establishment']=establishment
     book_reservation_intentInfo['booking_date']=today
     book_reservation_intentInfo['etype']=establishment_info['type']
     book_reservation_intentInfo['time_in']=time_in
     print('b1:', book_reservation_intentInfo)
     print(type(time_in),type(book_reservation_intentInfo['timeout']))
     
     flow['username']=uid
     return fulfillmentText
 
#yes - follow-up intent of BookAReservation
def bookAReservation_yes(req, Patron,name):
    flow['intent']='bookAReservation_yes'
    #intent_name=req['queryResult']['action'] #intent name
    intent_name='NewReservation'
    session_info=req['session'] #intent session
    book_reservation_intentInfo['fromIntent']=intent_name
    book_reservation_intentInfo['acknowledge']='Yes'
    print('timeout: ',book_reservation_intentInfo['timeout'])
    print( book_reservation_intentInfo['session'])
    timeout=book_reservation_intentInfo['timeout']
    ################## Pass Patron details time_in, n_person to rules  ##########################
    if timeout!='0':
        #ballot new 2
        print(book_reservation_intentInfo['session'], 
                            intent_name,
                              Patron, 
                              book_reservation_intentInfo['businessId'],
                              book_reservation_intentInfo['time_in'], 
                              timeout, 
                              book_reservation_intentInfo['No_of_Seats'])
        scode, msg, step = ira.Agent(book_reservation_intentInfo['session'], 
                            intent_name,
                              Patron, 
                              book_reservation_intentInfo['businessId'],
                              time_in=book_reservation_intentInfo['time_in'], 
                              time_out=book_reservation_intentInfo['timeout'], 
                              n_person=book_reservation_intentInfo['No_of_Seats']).check_rules()
        
    else:   
        #ballot new 1
        print(book_reservation_intentInfo['session'], 
                            intent_name,
                              Patron, 
                              book_reservation_intentInfo['businessId'],
                              book_reservation_intentInfo['time_in'], 
                              timeout, 
                              book_reservation_intentInfo['No_of_Seats'])
        scode, msg, step = ira.Agent(book_reservation_intentInfo['session'], 
                            intent_name,
                          Patron, 
                              book_reservation_intentInfo['businessId'],
                              time_in=book_reservation_intentInfo['time_in'],
                              n_person=book_reservation_intentInfo['No_of_Seats']).check_rules()
        
    ##################                                                     ##########################
     # fetch from IRA rules
    print('scode =',scode)
    print('msg=',msg)
    print('step=',step, type(step))
    print('\nfrom bookAReservation_yes', scode, msg, step)
    print('b1:', book_reservation_intentInfo)
   
    if scode=='0' and (step=='4' or step=='5' or step=='6' or step=='8' or step=='12' or step=='13'):
        #response_text=msg
        #response_text="%s confirms your slot booking for %s heads on %s.\n Thank you for choosing us"%(book_reservation_intentInfo['establishment'],book_reservation_intentInfo['No_of_Seats'],book_reservation_intentInfo['date_of_reservation'])
        response_text=msg
        suggestion_list=comm.process_suggestion(msg)
        print(type(suggestion_list))
        response_text="%s does not have the requested slots.\nInstead lists suggestions:\n "%(book_reservation_intentInfo['establishment'])
        response_text+='-'*45
        response_text+='\n'
        temp=''
        i=1
        for s in suggestion_list:
            temp+=str(i)+'. '+s+'\n'
            i+=1
        temp+='-'*45+'\n\nKey in your option ( e.g. 2): \n'
        # temp=suggestion_list
        book_reservation_intentInfo['suggestionlist']=suggestion_list
        response_text+=temp
        response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
    elif scode=='0' and (step=='10' or step=='11' or step=='2' ):
        m=msg.split('is')
        s=m[1]
        s=s.split('.')
        o=s[0].strip()
        o=o.split('to')
        a=o[0].strip()
        offer = datetime.datetime.strptime(a, '%A %d %B %Y at %H:%M')
        offer = datetime.datetime.strftime(offer, '%y/%m/%d_%H:%M')
        print(offer)
        book_reservation_intentInfo['offer']=offer
        response_text=msg
        response_text+=' Key [p] to proceed...'
        response_text+='\n'+'-'*45+'\n Key [ m ] to Main menu....'
    elif scode=='1' and (step=='1' or step=='3' or step=='4' or step=='5' or step =='6' or step=='7' or step=='8' or step=='9' or step=='10' )    :
        response_text=msg
        response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
           
    
    
    fulfillmentText = {'fulfillmentText': response_text}  
    
    print('b2:', book_reservation_intentInfo)
    return fulfillmentText 

def bookAReservation_yes_bruleok02(req, Patron,name) :
    intent_name='NewReservation'
    time_in=book_reservation_intentInfo['offer']
    print(time_in)
    selection=time_in
    scode, msg,step = ira.Agent(book_reservation_intentInfo['session'], 
                            intent_name,
                             Patron, 
                             book_reservation_intentInfo['businessId'], selection=selection).check_rules()
    print('bruleok02: ',scode, msg,step)
    if scode=='-1' and step=='5':
        response_text=msg
        response_text+='\n'+'-'*45+'\n\n Key [ m ] to Main menu....'
    elif scode=='1' and (step=='1' or step=='3' or step=='4'):
        response_text=msg
        response_text+='\n'+'-'*45+'\n\n Key [ m ] to Main menu....'
   
    print(response_text)
    #response_text+='You brule'
    fulfillmentText = {'fulfillmentText': response_text}  
    
    
    return fulfillmentText 

def bookAReservation_yes_bruleok02_confirm(req, Patron,name)    :
    intent_name='NewReservation'
    time_in=book_reservation_intentInfo['time_in']
    print(time_in)
    selection=time_in
    scode, msg,step = ira.Agent(book_reservation_intentInfo['session'], 
                            intent_name,
                             Patron, 
                             book_reservation_intentInfo['businessId'], selection=selection).check_rules()
    print('from confirm: ',scode, msg,step)
    response_text=msg
    fulfillmentText = {'fulfillmentText': response_text}  
    
    
    return fulfillmentText 

def bookAReservation_yes_followup(req, Patron,name):
    flow['intent']='bookAReservation_yes_followup'
    #intent_name=req['queryResult']['action'] #intent name
    intent_name='NewReservation'
    session_info=req['session'] #intent session
    book_reservation_intentInfo['fromIntent']=intent_name
    book_reservation_intentInfo['acknowledge']='Yes'
    option=req['queryResult']['parameters']['suggestion_list']
    
    print(option, type (option))
    suggestion_list=book_reservation_intentInfo['suggestionlist']
    option_value=suggestion_list[int(option)-1]
    if int(option)>len(suggestion_list) or int(option)<1 :
        response_text="Invalid entry!" 
    elif (option_value!=0):
        # customer chooses [selection]
        option_value=option_value.strip()
        print(option_value)
        selection=comm.process_date1_to_rules(option_value)
        print('selection:',selection)
        
         ################## Pass Patron selection to rules  ##########################
    
        
        response = ira.Agent(book_reservation_intentInfo['session'], 
                              intent_name, 
                              Patron, 
                              book_reservation_intentInfo['businessId'], 
                              selection=selection).check_rules()
       
        #book slot to rules ---use book_reservaton_intentInfo
        print('Response: \n',response, type(response))
        print('b3',book_reservation_intentInfo)
        
        #response_text+="%s says : %s ! Reservation CONFIRMED for %s.\n *** Have a nice day ! ***"%(book_reservation_intentInfo['establishment'], name,option_value)
        response_text=response[1]
        response_text+='\n\n'+'-'*45
        response_text+='\n Key [ m ] to return to Main menu...'
    else:
        response_text='Sorry about that. Bye Bye.\n'
    fulfillmentText = {'fulfillmentText': response_text}   
    print('b3:', book_reservation_intentInfo)
    return fulfillmentText 
    
#Function: process to cancel a reservation request

def cancel_a_reservation(req, Patron,name):
    #Fetch intent info
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='CancelReservation'
     session_info=req['session'] #intent parameters
     session_info=comm.process_session(session_info)
     session_info=str(session_info)
     establishment=process_establishmentname(req['queryResult']['parameters']['option'],establishment_info['type'])#Restaurant name
     uid=process_establishmentuid(req['queryResult']['parameters']['option'],establishment_info['type'])
     
     response_text=''
     cancel_reservation_intentInfo['userId']=Patron
     cancel_reservation_intentInfo['businessId']=str(uid)
     cancel_reservation_intentInfo['session']=session_info
     cancel_reservation_intentInfo['fromIntent']=intent_name
     cancel_reservation_intentInfo['establishment']=establishment
     
     ################## Fetch already booked slots from rules  ##########################
     # customer request with NO information
     scode, msg, step = ira.Agent(session_info, intent_name, Patron, cancel_reservation_intentInfo['businessId']).check_rules()
     print('c1 ',scode, msg, step )
     #agent=['Tuesday 20 October 2020 at 10:00', 'Tuesday 20 October 2020 at 09:40']
     if len(msg)>0:
         sl=comm.process_suggestion2(msg)
         response_text='Your upcoming reservation slot( s ):\n'+'-'*45+'\n'
         t=1
         for i in sl:
              response_text+= str(t)+'. '+i+'\n'
              t+=1
         response_text+='-'*45+'\n'+' Key your choice (e.g. 1) '
         response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
         cancel_reservation_intentInfo['already_booked_slots']=sl
     else:
         response_text=msg
     print('c1:',cancel_reservation_intentInfo)
    
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText

#Function: process to cancel a reservation request - confirm patron selection
def cancelAReservation_custom(req, patron, name):
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='CancelReservation'
     session_info=req['session'] #intent parameters
     session_info=str(session_info)
     op=req['queryResult']['parameters']['booked_slots_for_cancel']
     op=int(op)
     booked_slot_list=cancel_reservation_intentInfo['already_booked_slots']
     #cancel_reservation_intentInfo['session']=session_info
     #cancel_reservation_intentInfo['fromIntent']=intent_name
     cancel_reservation_intentInfo['selected_slot']=booked_slot_list[op-1]
     print(booked_slot_list[op-1])
     response_text='You have chosen '+booked_slot_list[op-1] + ' to Cancel.'
     print('cancel-custom: ',cancel_reservation_intentInfo)
     response_text+='\n\n'+'-'*45
     response_text+= '\n Yes or No? '
     response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
     fulfillmentText = {'fulfillmentText': response_text}
     #print(req['queryResult']['parameters'])
     return fulfillmentText

#Function: process to cancel a reservation request - 
            #Pass Patron selection to rules and recive response from rules
            
def cancelAReservation_custom_yes(req,Patron,name):
     print('cancel-custom-yes: ',cancel_reservation_intentInfo)
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='CancelReservation'
     session_info=req['session'] #intent parameters
     selection=comm.process_date1_to_rules(cancel_reservation_intentInfo['selected_slot'])
     print(selection)
      ################## Pass Patron selection to rules  ##########################
         
     response_text = ira.Agent(cancel_reservation_intentInfo['session'], cancel_reservation_intentInfo['fromIntent'], Patron, cancel_reservation_intentInfo['businessId'], selection=selection).check_rules()
     
     response_text= 'Reservation is cancelled SUCCESSFULLY!'
     response_text+='\n\n'+'-'*45
     response_text+='\n Key [ m ] to proceed to Main menu...'
     fulfillmentText = {'fulfillmentText': response_text}
     #print(req['queryResult']['parameters'])
     return fulfillmentText

#Function: process to change a reservation by date request

def change_by_date(req, Patron,name):
    #Fetch intent info
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='ChangeReservation'
     
     session_info=req['session'] #intent parameters
     session_info=comm.process_session(session_info)
     establishment=process_establishmentname(req['queryResult']['parameters']['option'],establishment_info['type'])#Restaurant name
     uid=process_establishmentuid(req['queryResult']['parameters']['option'],establishment_info['type'])
     
     response_text=''
     changeBydate_intentInfo['userId']=Patron
     changeBydate_intentInfo['businessId']=str(uid)
     changeBydate_intentInfo['session']=session_info
     changeBydate_intentInfo['fromIntent']=intent_name
     changeBydate_intentInfo['establishment']=establishment
     changeBydate_intentInfo['etype']=establishment_info['type']
     
      ################## # customer chooses [selection] from existing to change  ##########################
    
     scode, msg, step=ira.Agent(session_info, intent_name, Patron, changeBydate_intentInfo['businessId']).check_rules()
    
     print('change 1: ',scode, msg, step) 
     if scode=='-1' and step=='1':
         response_text=msg
         response_text+='\n Key [m] to Main menu'
     elif len(msg)>0:
         sl=comm.process_suggestion2(msg)
         response_text='Your upcoming reservation slot( s ):\n'+'-'*45+'\n'
         t=1
         for i in sl:
              response_text+= str(t)+'. '+i+'\n'
              t+=1
         response_text+='-'*45+'\n'+' Key your choice (e.g. 1) '
         response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
         changeBydate_intentInfo['already_booked_slots']=sl
     print('change:',changeBydate_intentInfo)
     #response_text='change'
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText

#Function: Select one of the booked slot to change
def ChangeByDate_custom(req, Patron, name):    
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='ChangeReservation'
     session_info=changeBydate_intentInfo['session'] #intent parameters   
     op=req['queryResult']['parameters']['booked_slots_for_change']
     op=int(op)
     booked_slot_list=changeBydate_intentInfo['already_booked_slots']
     changeBydate_intentInfo['session']=session_info
     changeBydate_intentInfo['fromIntent']=intent_name
     changeBydate_intentInfo['selection1']=booked_slot_list[op-1]
     print(booked_slot_list[op-1])
     response_text='You have chosen '+booked_slot_list[op-1] + ' to Change.'
     print('change-custom: ',changeBydate_intentInfo)
     response_text+='\n\n'+'-'*45
     response_text+= '\n Yes or No? '
     response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
     fulfillmentText = {'fulfillmentText': response_text}
     #print(req['queryResult']['parameters'])
     return fulfillmentText

#Function: Selection1 passed to Agebt & collect change requirements from patron-seats, date, time
def ChangeByDate_custom_yes(req, Patron, name):
     intent_name='ChangeReservation'
     #intent_name=req['queryResult']['action'] #intent name
     session_info=changeBydate_intentInfo['session'] #intent session
     selection=comm.process_date1_to_rules(changeBydate_intentInfo['selection1'])
     print('selection: ',selection)
      ################## selection1 to rules  ##########################
    
     scode, msg,step = ira.Agent(session_info, intent_name, Patron,  changeBydate_intentInfo['businessId'], selection=selection).check_rules()
     print('change 3: ', scode,msg,step)
     if scode=='-1' and step=='1':
         response_text=msg
         response_text+='\n Key [m] to Main menu'
     elif scode=='1' and step=='1':
         response_text=msg
         response_text+='\n Key [m] to Main menu'
     elif scode=='0' and step=='2':
         print('0,2:',msg)
         print(req['queryResult']['parameters'])
         response_text='IRA expects details of change..'
         response_text+='\n Key [ p ] to proceed...'
         # 
         # print(response_text)
         
     else:
         
        response_text='hahah'
     
     print('change-yes:',changeBydate_intentInfo)
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText
 
#Function: Pass the collected details to rules
def ChangeByDate_custom_yes_ok(req, Patron, name):
     #intent_name=req['queryResult']['action'] #intent name
     print(req['queryResult']['parameters'])
     intent_name='ChangeReservation'
     session_info=changeBydate_intentInfo['session'] #intent session
     
     changeBydate_intentInfo['fromIntent']=intent_name
     timein=req['queryResult']['parameters']['ctime']
     ts=isoformatTimetoString(timein)
     print(ts)
     ts=datetime.datetime.strptime(ts, '%H:%M:%S')
     ts=datetime.datetime.strftime(ts, '%H:%M')
     print('ts:',ts, type(ts))
     n_person=int(req['queryResult']['parameters']['seats']) # No of seats
     date_request=req['queryResult']['parameters']['cdate'] # date_of_reservation
     date_request,dor=isodateToString(date_request)
     d=datetime.datetime.strftime(dor, '%y/%m/%d')
     time_in=str(d)+'_'+str(ts)
     time_in=datetime.datetime.strptime(time_in,'%y/%m/%d_%H:%M')
     time_in=datetime.datetime.strftime(time_in,'%y/%m/%d_%H:%M')
     print(time_in)
     changeBydate_intentInfo['session']=session_info
     changeBydate_intentInfo['fromIntent']=intent_name
     changeBydate_intentInfo['change_date_request']=date_request
     changeBydate_intentInfo['seat_request']=n_person
     changeBydate_intentInfo['timein_request']=ts
     print(changeBydate_intentInfo)
     response_text='You have requested a change to '+changeBydate_intentInfo['change_date_request']
     response_text+=' at '+changeBydate_intentInfo['timein_request']
     response_text+=' for '+ str(changeBydate_intentInfo['seat_request'])+' persons. '
     response_text+='\nIRA checks for availability... [ ok ]'
     #changeBydate_intentInfo['time_in']=changeBydate_intentInfo['change_date_request']+' at '+changeBydate_intentInfo['timein_request']
     changeBydate_intentInfo['time_in']=time_in
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText
 
#Function: Choose the option from available slots & Selection2 update changes to rules
def ChangeByDate_custom_yes_ok_selectlist(req, Patron, name):
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='ChangeReservation'
     session_info=changeBydate_intentInfo['session'] #intent session
     print('yes-ok-selectlist', changeBydate_intentInfo)
     time_in=changeBydate_intentInfo['time_in']
     n_person=changeBydate_intentInfo['seat_request']
     scode, msg, step = ira.Agent(session_info, intent_name, Patron, 
                                  changeBydate_intentInfo['businessId'], time_in=time_in, n_person=n_person).check_rules()
     print('change yes ok list: ', scode, msg, step)
     if scode=='0' and (step=='9' or step=='10'):
         sl=comm.process_suggestion3(msg)
         response_text='Available slot( s ):\n'+'-'*45+'\n'
         t=1
         for i in sl:
              response_text+= str(t)+'. '+i+'\n'
              t+=1
         response_text+='-'*45+'\n'+' Key your choice (e.g. 1) '
         response_text+='\n'+'-'*45+'\nKey [ m ] to Main menu...'
         changeBydate_intentInfo['available_slots']=sl
     elif scode=='1' and (step=='4'or step=='5' or step=='6' or step=='7' or step=='8'):  
          response_text=msg
          response_text+='\n Key [ m ] to Main menu....'
     print('changeyes ok list:',changeBydate_intentInfo)
     
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText 


def ChangeByDate_custom_yes_ok_selectlist_number(req, Patron, name) :
     intent_name='ChangeReservation'
     session_info=changeBydate_intentInfo['session'] #intent session
     print(req['queryResult']['parameters'])
     print('yes-ok-selectlist-number', changeBydate_intentInfo)
     num=req['queryResult']['parameters']['number']
     num=int(num)
     available_slots=changeBydate_intentInfo['available_slots']
     print(available_slots)
     print(available_slots[num-1])
     selection2=comm.process_date1_to_rules(available_slots[num-1])
     print('selection2: ',selection2)
     scode, msg, step = ira.Agent(session_info, intent_name, Patron, changeBydate_intentInfo['businessId'], selection=selection2).check_rules()
     print('change yes ok list num:',scode, msg, step)
     response_text=msg
     #if scode=='0' and step=='3':
     response_text+='\n'+'-'*45+'\n Key [ m ] to Main menu...'
         
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText

    
#Function: process to change a reservation by date request

def check_reservation(req, Patron,name):
    #Fetch intent info
     #intent_name=req['queryResult']['action'] #intent name
     intent_name='CheckReservation'
    
     session_info=req['session'] #intent parameters
     session_info=comm.process_session(session_info)
     establishment=process_establishmentname(req['queryResult']['parameters']['option'],establishment_info['type'])#Restaurant name
     uid=process_establishmentuid(req['queryResult']['parameters']['option'],establishment_info['type'])
     
     check_reservation_intentInfo['userId']=Patron
     check_reservation_intentInfo['businessId']=str(uid)
     check_reservation_intentInfo['session']=session_info
     check_reservation_intentInfo['fromIntent']=intent_name
     check_reservation_intentInfo['establishment']=establishment
     check_reservation_intentInfo['etype']=establishment_info['type']
     
      ################## # customer chooses [selection] from existing to change  ##########################
  
     scode, msg, step=ira.Agent(session_info, intent_name, Patron, check_reservation_intentInfo['businessId']).check_rules()
     print('check: ',scode, msg, step, len(msg) )
     
     response_text='Your upcoming reservation slot( s ):\n'+'-'*45+'\n'
     
     response_text=msg
     response_text+='\n'+'-'*45+'\n Key [ m ] for Main menu... '
     #     check_reservation_intentInfo['available_slots']=sl
     print('check:',check_reservation_intentInfo)
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText
    


#Function to fetch company details    
def about_company(req,Patron,name) :
    
     intent_name=req['queryResult']['action'] #intent name
     para=req['queryResult']['parameters'] #intent parameters
     print(para)
     session_info=req['session'] #intent parameters
     session_info=comm.process_session(session_info)
     op=req['queryResult']['parameters']['option']
     elist=[]
     elist=flow['elist']
     count=len(elist)
     if int(op)>count :
         response_text="Invalid entity number"
     else:
         establishment=process_establishmentname(op,establishment_info['type'])#Restaurant name
         uid=process_establishmentuid(op,establishment_info['type'])
         data=comm.load_company_details_from_table(uid)
         print(data)
         d=data[0]
         result=[]
         j=0
         for i in d:
             result+=[i]
             j+=1
         print(result)
         company=result[0]
         location=result[1]
         contact=result[2]
         max_cap=result[3]
         open_days=result[4]
         open=open_days
         if open=='1':
            open='Mon'
         elif open=='12':
            open='Mon Tue'
         elif open=='123':
            open='Mon Tue Wed'
         elif open=='1234':
            open='Mon Tue Wed Thu'
         elif open=='12345':
            open='Mon Tue Wed Thu Fri'
         elif open=='123456':
            open='Mon Tue Wed Thu Fri Sat'
         elif open=='1234567':
            open='Mon Tue Wed Thu Fri Sat Sun'
         open_days=open
         open_time=result[5]
         close_time=result[6]
         #company,location,contact, max_cap, open_days, open_time, close_time
         
         
         response_text="%s\n ---------------------------------\n Address:   %s \nOpen on : %s \n Opening time:  %s\n Closing time:  %s\n Contact @: %s  "%(company,location, open_days, open_time, close_time,contact)
     response_text+='\n'+'-'*45
     response_text+='\n\n Key [ m ] to Main Menu...'
     fulfillmentText = {'fulfillmentText': response_text}
     return fulfillmentText 
    
 

#Function: process to change a reservation by adding more seats request

# def add_more_seats(req, Patron):
#     #Fetch intent info
#      intent_name=req['queryResult']['action'] #intent name
#      session_info=req['session'] #intent parameters
#      establishment=process_establishmentname(req['queryResult']['parameters']['option'],establishment_info['type'])#Restaurant name
#      uid=process_establishmentuid(req['queryResult']['parameters']['option'],establishment_info['type'])    
#      date_of_reservation=req['queryResult']['parameters']['booked_day'] # date_of_reservation
#      date_of_reservation_txt,dor=isodateToString(date_of_reservation)
#      today=datetime.datetime.today()
#      response_text=''
     
#      num_of_seats=req['queryResult']['parameters']['seats'] # number of seats
#      num_of_seats=int(num_of_seats)
#      if dor<today :
#          response_text='Invalid date keyed in. Retry a new request for adding more seats'
#          fulfillmentText = {'fulfillmentText': response_text}
#      elif num_of_seats<2 or num_of_seats>5:
#          response_text='Min 2 Seats and Max 5 Seats only allowed.Retry a new request for Booking'
#          fulfillmentText = {'fulfillmentText': response_text}
#      else:
#         response_text='%s says : You have requested to add %d more seats for the reservation date %s.\nPlease confirm to proceed (Yes/No)...'%(establishment, num_of_seats,date_of_reservation_txt)
#         fulfillmentText = {'fulfillmentText': response_text} 
        
#      addMoreseats_intentInfo['userId']=Patron
#      addMoreseats_intentInfo['businessId']=uid
#      addMoreseats_intentInfo['session']=session_info
#      addMoreseats_intentInfo['num_of_seats']=num_of_seats
#      addMoreseats_intentInfo['date_of_reservation']=date_of_reservation_txt
#      addMoreseats_intentInfo['fromIntent']=intent_name
#      addMoreseats_intentInfo['establishment']=establishment
#      addMoreseats_intentInfo['etype']=establishment_info['type']
#      return fulfillmentText 

# #yes - follow-up intent of addSeats
# def addMoreSeats_yes(req, Patron,name):
#     intent_name=req['queryResult']['action'] #intent name
#     response_text=name +"!You said Yes" #to be changed
#     fulfillmentText = {'fulfillmentText': response_text}   
#     reduceSeats_intentInfo['fromIntent']=intent_name
#     reduceSeats_intentInfo['acknowledge']='Yes'
#     print(reduceSeats_intentInfo)
#     return fulfillmentText 

# #Function: process to change a reservation by reducing more seats request

# def reduce_seats(req, Patron):
#     #Fetch intent info
#      intent_name=req['queryResult']['action'] #intent name
#      session_info=req['session'] #intent parameters
#      establishment=process_establishmentname(req['queryResult']['parameters']['option'],establishment_info['type'])#Restaurant name
#      uid=process_establishmentuid(req['queryResult']['parameters']['option'],establishment_info['type'])
#      date_of_reservation=req['queryResult']['parameters']['booked_day'] # date_of_reservation
#      date_of_reservation_txt,dor=isodateToString(date_of_reservation)
#      today=datetime.datetime.today()
#      response_text=''
     
#      num_of_seats=req['queryResult']['parameters']['seats'] # number of seats to reduce
#      num_of_seats=int(num_of_seats)
#      if dor<today :
#          response_text='Invalid date keyed in. Retry a new request for adding more seats'
#          fulfillmentText = {'fulfillmentText': response_text}
#      elif num_of_seats<1 or num_of_seats>4:
#          response_text='Min 2 Seats and Max 5 Seats only allowed.Retry a new request for Booking'
#          fulfillmentText = {'fulfillmentText': response_text}
#      else:
#         response_text='%s says : You have requested to reduce %d seats for the reservation date %s.\nPlease confirm to proceed (Yes/No)...'%(establishment, num_of_seats,date_of_reservation_txt)
#         fulfillmentText = {'fulfillmentText': response_text} 
     
#      reduceSeats_intentInfo['userId']=Patron
#      reduceSeats_intentInfo['businessId']=uid
#      reduceSeats_intentInfo['session']=session_info
#      reduceSeats_intentInfo['num_of_seats']=num_of_seats
#      changeBydate_intentInfo['date_of_reservation']=date_of_reservation_txt
#      reduceSeats_intentInfo['fromIntent']=intent_name
#      reduceSeats_intentInfo['establishment']=establishment
#      reduceSeats_intentInfo['etype']=establishment_info['type']
#      return fulfillmentText 
 
# #yes - follow-up intent of reduceSeats
# def reduceSeats_yes(req, Patron,name):
#     intent_name=req['queryResult']['action'] #intent name
#     response_text=name +"!You said Yes" #to be changed
#     fulfillmentText = {'fulfillmentText': response_text}   
#     reduceSeats_intentInfo['fromIntent']=intent_name
#     reduceSeats_intentInfo['acknowledge']='Yes'
#     print(reduceSeats_intentInfo)
#     return fulfillmentText 


