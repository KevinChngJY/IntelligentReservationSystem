# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .models import establishments, patrons, reservations, queries, business_register, rsv_report, qry_report
from django.template import loader
from social_django.models import UserSocialAuth
from django.core.exceptions import ObjectDoesNotExist
import random
import datetime
import re
from django.db.models.expressions import RawSQL
import pandas as pd
import sqlite3

#Google Diaglog flow
from django.views.decorators.csrf import csrf_exempt
import json
from . import dialogflow_communications as dc
from . import communications_channel as comm
global patron, name
name=''
patron=''
user_details={}

#form.py
from . import form_submission as formsub

#Ngrok Configuration
ngrok_address = 'https://c3f738f3963e.ngrok.io/'
#Facebook valid OAuth Redirect URIs02adf2cec585.ngrok.io
#https://c3f738f3963e.ngrok.io/intelligentreservationagent/login/
#https://c3f738f3963e.ngrok.io/intelligentreservationagent/social-auth/complete/facebook
#https://c3f738f3963e.ngrok.io/intelligentreservationagent/home/

## Business Dashboard
def business_registration(request):
	ngrok_address2 = ngrok_address
	if request.session.has_key('username'):
		username = request.session['username']
		c = establishments.objects.filter(email=username)
		k = range(1,len(c)+1)
		mylist = zip(k , c)
		context = {'username' : username,'mylist' : mylist,'ngrok_address2' : ngrok_address2}
		if request.method == 'POST':
			if 'save' in request.POST:
				username=request.session['username']
				company = request.POST.get('company')
				uniqueid = request.POST.get('unique_id')
				location = request.POST.get('location')
				contact = request.POST.get('contact')
				e_type = request.POST.get('typeBusiness')
				if e_type=="Restaurant":
					sublocation = request.POST.get('sublocation')
				maxcapacity = request.POST.get('maxcapacity')
				opentime = request.POST.get('opentime').replace(':','')
				closetime = request.POST.get('closetime').replace(':','')
				defaulttime = request.POST.get('defaulttime')
				maxgroupsize = request.POST.get('maxgroupsize')
				openmonday = request.POST.get('openmonday')
				opentuesday = request.POST.get('opentuesday')
				openwednesday = request.POST.get('openwednesday')
				openthursday = request.POST.get('openthursday')
				openfriday = request.POST.get('openfriday')
				opensaturday = request.POST.get('opensaturday')
				opensunday = request.POST.get('opensunday')
				openmonday = '1' if openmonday else ''
				opentuesday = '2' if opentuesday else ''
				openwednesday = '3' if openwednesday else ''
				openthursday = '4' if openthursday else ''
				openfriday = '5' if openfriday else ''
				opensaturday = '6' if opensaturday else ''
				opensunday = '7' if opensunday else ''
				opendate = openmonday+opentuesday+openwednesday+openthursday+openfriday+opensaturday+opensunday
				sendreminder = request.POST.get('sendreminder')
				sendreminder= True if sendreminder else False
				reportingperiod = request.POST.get('reportingperiod')
				reportingperiod = '7' if reportingperiod=='Weekly' else '14'
				isadvance = str(request.POST.get('isadvance'))
				#To save modification information
				try:
					q = establishments.objects.get(username=uniqueid)
					if e_type=="Resaurant":
						establishments.objects.filter(username=uniqueid).update(company=company,location=location,type_business=e_type,
						contact=contact,sublocs=sublocation,max_cap=maxcapacity,open_days=opendate,open_time=opentime,
						close_time=closetime,default_duration=defaulttime,max_group_size=maxgroupsize,
						report_period =reportingperiod,is_reminder=sendreminder)
					else:
						establishments.objects.filter(username=uniqueid).update(company=company,location=location,type_business=e_type,
						contact=contact,max_cap=maxcapacity,open_days=opendate,open_time=opentime,
						close_time=closetime,default_duration=defaulttime,max_group_size=maxgroupsize,
						report_period=reportingperiod,is_reminder=sendreminder,days_in_advance=isadvance)		
				#To save new information
				except ObjectDoesNotExist:
					while(1):
						uniqueid = random.randint(1,30000)
						check2=establishments.objects.filter(username=str(uniqueid))
						if check2:
							pass
						else:
							break;
					if e_type=="Resaurant":
						q = establishments(username=uniqueid,email=username,company=company,location=location,
						type_business=e_type,contact=contact,sublocs=sublocation,max_cap=maxcapacity,open_days=opendate,
						open_time=opentime,close_time=closetime,default_duration=defaulttime,max_group_size=maxgroupsize,
						report_period =reportingperiod,is_reminder=sendreminder)
					else:
						q = establishments(username=uniqueid,email=username,company=company,location=location,
						type_business=e_type,contact=contact,max_cap=maxcapacity,open_days=opendate,
						open_time=opentime,close_time=closetime,default_duration=defaulttime,max_group_size=maxgroupsize,
						report_period =reportingperiod,is_reminder=sendreminder,days_in_advance=isadvance)
					q.save()
					c = establishments.objects.filter(email=username)
					k = range(1,len(c)+1)
					mylist = zip(k , c)
					context = {'username' : username,'mylist' : mylist}
			if 'modify' in request.POST:
				uniqueid = request.POST.get('modify')
				d = establishments.objects.get(username=uniqueid)
				d.open_time = d.open_time[0:2] + ":" +d.open_time[2:4]
				d.close_time = d.close_time[0:2] + ":" +d.close_time[2:4]
				print(d.open_time)
				if d.type_business!="Restaurant":
					d.days_in_advance = int(d.days_in_advance)
				openmonday = True if "1" in d.open_days  else False
				opentuesday = True if "2" in d.open_days else False
				openwednesday = True if "3" in d.open_days else False
				openthursday = True if "4" in d.open_days else False
				openfriday = True if "5" in d.open_days else False
				opensaturday = True if "6" in d.open_days else False
				opensunday = True if "7" in d.open_days else False
				reportingperiod = 'Weekly' if d.report_period=='7' else 'Biweekly'
				template = loader.get_template("Business_registration.html")
				return HttpResponse(template.render(locals(),request))
			if 'delete' in request.POST:
				uniqueid = request.POST.get('delete')
				establishments.objects.get(username=uniqueid).delete()
				template = loader.get_template("Business_registration.html")
				c = establishments.objects.filter(email=username)
				k = range(1,len(c)+1)
				mylist = zip(k , c)
				context = {
					'username' : username,
					'mylist' : mylist
					}
				return HttpResponse(template.render(locals(),request))
		template = loader.get_template("Business_registration.html")
		return HttpResponse(template.render(context,request))
	else:
		return redirect('/intelligentreservationagent/login_business')

def business_profile(request):
	ngrok_address2 = ngrok_address
	if request.session.has_key('username'):
		username=request.session['username']
		template = loader.get_template("business_profile.html")
		if request.method == 'POST':
			if 'save' in request.POST:
				person = request.POST.get('person')
				contact = request.POST.get('contact')
				address = request.POST.get('address')
				business_register.objects.filter(business_email=username).update(business_incharge_person=person,business_contact=contact,business_mail_address=address)
				notification = " Success Update Profile"
			if 'change' in request.POST:
				check='2'
			if 'changpassword' in request.POST:
				oldpassword = request.POST.get('OldPassword')
				newpassword1 = request.POST.get('NewPassword1')
				newpassword2 = request.POST.get('NewPassword2')
				d = business_register.objects.get(business_email=username)
				if d.business_password==oldpassword:
					verification=password_check(newpassword1)
					if verification == True:
						if newpassword1==newpassword2:
							business_register.objects.filter(business_email=username).update(business_password=newpassword1)
							notification = " Success Update Password"
						else:
							notification = "New Confirmed Password is not matched"
							check='2'
					else:
						check='2'
						notification = "New Password must follow : "
						notification1= "1) Your password must be between 6 and 20 characters."
						notification2= "2) Your password must be at least one numeral."
						notification3= "3) Your password must be at least one uppercase letter."
						notification4= "4) Your password must be at least one lowercase letter."
				else:
					check='2'
					notification = "Old Password is Wrong"
		d = business_register.objects.get(business_email=username)
		return HttpResponse(template.render(locals(),request))
	else:
		return redirect('/intelligentreservationagent/login_business')
	
def business_logout(request):
	ngrok_address2 =ngrok_address
	try:
		username=request.session['username']
		del request.session['username']
	except:
		pass
	template = loader.get_template("business_logout.html")
	return HttpResponse(template.render(locals(),request))

def business_dashboard(request):
	ngrok_address2 = ngrok_address
	if request.session.has_key('username'):
		if request.method == 'POST':
			if 'GA' in request.POST:
				formsub.GA_housekeeping()
			if 'SL' in request.POST:
				formsub.SL_housekeeping()
		username=request.session['username']
		template = loader.get_template("Business_dashboard.html")
		try:
			establishment=establishments.objects.filter(email=username)
			query = "SELECT * FROM nus_reservations as nus_r INNER JOIN nus_establishments as nus_e ON nus_r.establishment = nus_e.username INNER JOIN nus_patrons as nus_p ON nus_r.patron =nus_p.username WHERE nus_e.email = '%s'" % username
			user_reservations_info = reservations.objects.raw(query)
			for user in user_reservations_info:
				user.time_in = datetime.datetime.strptime('20%s' % user.time_in, "%Y/%m/%d_%H:%M")
				user.time_out = datetime.datetime.strptime('20%s' % user.time_out, "%Y/%m/%d_%H:%M")
			reservation_list = [user for user in user_reservations_info]
			reservation_list = sorted(reservation_list, key=lambda x: x.time_in)
			k = range(1,len(user_reservations_info)+1)
			mylist = zip(k , user_reservations_info)
		except Exception as e :
			print(e)
		return HttpResponse(template.render(locals(),request))
	else:
		return redirect('/intelligentreservationagent/login_business')

def load_table(tn, db='dummy.db'):
    conn = sqlite3.connect(db)
    df = pd.read_sql(f"SELECT * FROM {tn}", conn)
    conn.close()
    del conn
    return df

def business_dashboard2(request):
	ngrok_address2 = ngrok_address
	if request.session.has_key('username'):
		username=request.session['username']
		template = loader.get_template("Business_dashboard2.html")
		try:
			establishment=establishments.objects.filter(email=username)
			query = "SELECT * FROM nus_queries as nus_r INNER JOIN nus_establishments as nus_e ON nus_r.establishment = nus_e.username INNER JOIN nus_patrons as nus_p ON nus_r.patron =nus_p.username WHERE nus_e.email = '%s'" % username
			user_reservations_info = queries.objects.raw(query)
			reservation_list = [user for user in user_reservations_info]
		except Exception as e :
			print(e)
		if request.method == 'POST':
			formsub.summary_query()
			df = load_table('nus_qry_report', 'db.sqlite3')
			data=df.to_html()
			template = loader.get_template("Business_dashboard2_sub.html")
			return HttpResponse(template.render(locals(),request))
		return HttpResponse(template.render(locals(),request))
	else:
		return redirect('/intelligentreservationagent/login_business')


def business_dashboard3(request):
	ngrok_address2 = ngrok_address
	if request.session.has_key('username'):
		username=request.session['username']
		template = loader.get_template("Business_dashboard3.html")
		if request.method == 'POST':
			uniqueid_timestamp= request.POST.get('Hourly')
			user_reservation_info = rsv_report.objects.get(timestamp=uniqueid_timestamp)
			dfied = pd.DataFrame.from_dict(json.loads(user_reservation_info.hourly))
			data=dfied.to_html()
			template = loader.get_template("Business_dashboard3_sub.html")
			return HttpResponse(template.render(locals(),request))
		try:
			query = "SELECT * FROM nus_rsv_report as nus_r INNER JOIN nus_establishments as nus_e ON nus_r.establishment = nus_e.username WHERE nus_e.email='%s'" % username
			user_reservation_info = rsv_report.objects.raw(query)
			print(len(user_reservation_info))
			reservation_list = [user for user in user_reservation_info]
		except Exception as e :
			print(e)
		return HttpResponse(template.render(locals(),request))
	else:
		return redirect('/intelligentreservationagent/login_business')

# Create your views here.
def login1_business(request):
	ngrok_address2 = ngrok_address
	if request.method == 'POST':
		business_email = request.POST.get('email')
		business_password1 = request.POST.get('password')
		try:
			c = business_register.objects.get(business_email=business_email)
		except Exception as e:
			msg = "Email is not registered!"
			template = loader.get_template("business_login.html")
			return HttpResponse(template.render(locals(),request))
		if c.business_password!=business_password1:
			msg = "Password is unmatched"
			template = loader.get_template("business_login.html")
			return HttpResponse(template.render(locals(),request))
		request.session['username'] = business_email
		return redirect('/intelligentreservationagent/business_dashboard')
	return HttpResponse(render(request, "business_login.html"))

def password_check(passwd): 
	val = True
	if len(passwd) < 6: 
		val = False
	if len(passwd) > 20: 
		val = False
	if not any(char.isdigit() for char in passwd): 
		val = False
	if not any(char.isupper() for char in passwd): 
		val = False
	if not any(char.islower() for char in passwd):
		val = False
	return val 

def signup(request):
	ngrok_address2 = ngrok_address
	if request.method == 'POST':
		business_email = request.POST.get('email')
		business_person = request.POST.get('person')
		business_password1 = request.POST.get('password1')
		business_password2 = request.POST.get('password2')
		verification=password_check(business_password1)
		b = False
		try:
			c = business_register.objects.get(business_email=business_email)
		except Exception as e:
			b = True
		if b == False:
			template = loader.get_template("fail_signup2.html")
			return HttpResponse(template.render(locals(),request))
		elif verification==False:
			template = loader.get_template("fail_signup.html")
			return HttpResponse(template.render(locals(),request))
		elif business_password1 != business_password2:
			template = loader.get_template("fail_signup1.html")
			return HttpResponse(template.render(locals(),request))
		else:
			try:
				id_num=business_register.objects.all().order_by("-id")[0]
				id_num1 = int(id_num.business_id)+1
				id_num1 = str(id_num1)
			except:
				id_num1 = 1
			q = business_register(business_id=id_num1, business_email=business_email,business_incharge_person=business_person, business_password=business_password1)
			q.save()
			template = loader.get_template("success_signup.html")
			return HttpResponse(template.render(locals(),request))
	return HttpResponse(render(request, "signup.html"))

def business_support(request):
	ngrok_address2 = ngrok_address
	if request.session.has_key('username'):
		template = loader.get_template("support2.html")
		return HttpResponse(template.render(locals(),request))
	else:
		return redirect('/intelligentreservationagent/login_business')

@login_required
def index(request):
	#forhamsi #Connect to dialogflow
	comm.post_establishment_entity_to_bot()  #initialise restaurant entity in bot
	comm.post_c_establishment_entity_to_bot() #initialise clinic entity in bot
	comm.post_s_establishment_entity_to_bot()  #initialise shop entity in bot
	user=request.user
	patron=user.social_auth.get(provider='facebook').uid
	first_name=user.social_auth.get(provider='facebook').extra_data['first_name']
	second_name=user.social_auth.get(provider='facebook').extra_data['last_name']
	email=user.social_auth.get(provider='facebook').extra_data['email']
	name = first_name + ' ' + second_name

	user_details['name']=name
	user_details['patron']=patron

	#Save Patrons to database
	check1=patrons.objects.filter(username=patron)
	if check1:
		pass
	else:
		patrons(username=patron,first_name=first_name,second_name=second_name,email=email).save()

	# user.social_auth.get(provider='facebook').extra_data.last_name 
	ngrok_address2 = ngrok_address
	all_establishment_register = establishments.objects.all()
	today = datetime.date.today()
	d1 = today.strftime("%Y-%m-%d")
	context = {
	'all_establishment_register': all_establishment_register,
	}
	while(1):
		session = random.randint(1000001,60000000000)
		check2=reservations.objects.filter(session=str(session))
		if check2:
			pass
		else:
			break;
	if request.method == 'POST':
		if 'reserve_button' in request.POST:
			session = request.POST.get('sessionid')
			restablishment = request.POST.get('dropdown')
			reservationdate = request.POST.get('reservationdate')
			reservationtime = request.POST.get('reservationtimein')
			combine_date_time = reservationdate+'T'+reservationtime
			reservationtimeout = request.POST.get('reservationtimeout')
			combine_date_timeout = reservationdate+'T'+reservationtimeout
			reservationdate = datetime.datetime.strptime(reservationdate, "%Y-%m-%d").date()
			People = request.POST.get('People')
			address = request.POST.get('location')
			check1=reservations.objects.filter(session=session)
			if check1:
				dt =  datetime.datetime.strptime(combine_date_time.replace(':',''),"%Y-%m-%dT%H%M")
				dt = datetime.datetime.strftime(dt,'%y/%m/%d_%H:%M')
				businessId=restablishment
				check1=reservations.objects.get(session=session)
				scode, msg =formsub.change_a_reservation(patron,businessId,session,dt,People,check1.time_in)
				if scode =="-1":
					while(1):
						session = random.randint(1000001,60000000000)
						check2=reservations.objects.filter(session=str(session))
						if check2:
							pass
						else:
							break;
					context = {'msg' : msg, 'ngrok_address2' : ngrok_address, 'session' : session}
					template = loader.get_template('NUS_dashboard_1.html')
					return HttpResponse(template.render(context,request))
				elif scode =="1":
					while(1):
						session = random.randint(1000001,60000000000)
						check2=reservations.objects.filter(session=str(session))
						if check2:
							pass
						else:
							break;										
					context = {'msg' : msg, 'ngrok_address2' : ngrok_address, 'session' : session}
					template = loader.get_template('NUS_dashboard_1.html')
					return HttpResponse(template.render(context,request))
				elif scode =="0" and msg[0]=="A":
					ind1=msg.index('(1)')
					ind2=msg.index('(2)')
					ind3=msg.index('(3)')
					ind4=msg.index('(4)')
					ind5=msg.index('(5)')
					option1=msg[ind1:ind2]
					option2=msg[ind2:ind3]
					option3=msg[ind3:ind4]
					option4=msg[ind4:ind5]
					option5=msg[ind5:]
					context = {'option1':option1, 'option2':option2, 'option3':option3, 
					'option4':option4, 'option5':option5, 'businessId':businessId, 'session' : session, 'button' : 'option2'}
					template = loader.get_template('NUS_dashboard_0_offer.html')
					return HttpResponse(template.render(context,request))
			else:
				dt =  datetime.datetime.strptime(combine_date_time.replace(':',''),"%Y-%m-%dT%H%M")
				dt = datetime.datetime.strftime(dt,'%y/%m/%d_%H:%M')
				dt2 =  datetime.datetime.strptime(combine_date_timeout.replace(':',''),"%Y-%m-%dT%H%M")
				dt2 = datetime.datetime.strftime(dt2,'%y/%m/%d_%H:%M')
				businessId=restablishment
				scode, msg =formsub.book_a_reservation(patron,businessId,session,dt,dt2,People,reservationdate)
				#q =user_reservation(id_unique=uniqueid,user_id=user.social_auth.get(provider='facebook').uid,establishment=restablishment,location=address,Reservation_date=reservationdate,Reservation_time=reservationtime,Number_people=People)
				#q.save()
				if scode =="1":
					context = {'msg' : msg, 'ngrok_address2' : ngrok_address, 'session' : session}
					template = loader.get_template('NUS_dashboard_1.html')
					return HttpResponse(template.render(context,request))
				elif scode =="0" and msg[0]=="T":
					establishment = establishments.objects.get(username=businessId)
					ind1=msg.index(':')
					dt = msg[ind1-2:ind1+3]
					ind2=msg[ind1+1:].index(':')
					dt2 =msg[ind1+ind2-1:ind1+ind2+4]
					context = {'msg' : msg,'businessId':businessId, 'session' : session,'dt': dt,'dt2':dt2,'reservationdate':reservationdate,'People':People,'establishment':establishment}
					template = loader.get_template('NUS_dashboard_0.html')
					return HttpResponse(template.render(context,request))
				elif scode =="0" and msg[0]=="A":
					ind1=msg.index('(1)')
					ind2=msg.index('(2)')
					ind3=msg.index('(3)')
					ind4=msg.index('(4)')
					ind5=msg.index('(5)')
					option1=msg[ind1:ind2]
					option2=msg[ind2:ind3]
					option3=msg[ind3:ind4]
					option4=msg[ind4:ind5]
					option5=msg[ind5:]
					context = {'option1':option1, 'option2':option2, 'option3':option3, 
					'option4':option4, 'option5':option5, 'businessId':businessId, 'session' : session, 'button' : 'option'}
					template = loader.get_template('NUS_dashboard_0_offer.html')
					return HttpResponse(template.render(context,request))
				#now = datetime.datetime.now()
				#user_notification(id_unique=uniqueid,user_id=user.social_auth.get(provider='facebook').uid,intends="New Reservation",notification="Success :"+restablishment+","+str(reservationdate)+" "+reservationtime,datetime=now).save()
		if 'modify' in request.POST:
			info = request.POST.get('modify')
			b = reservations.objects.get(session=info)
			c = establishments.objects.get(username=b.establishment)
			reservationdate_in=datetime.datetime.strptime(b.time_in[0:8],"%y/%m/%d")
			b.time_in=b.time_in[-5:]
			b.time_out=b.time_out[-5:]
		if 'delete' in request.POST:
			id_num = request.POST.get('delete')
			check1=reservations.objects.get(session=id_num)
			scode, msg =formsub.cancel_a_reservation(patron,check1.establishment,session,check1.time_in)
		if 'fail' in request.POST:
			session = request.POST.get('fail')
		if 'confirmed_button' in request.POST:
			session = request.POST.get('sessionid')
			businessid = request.POST.get('businessid')
			reservationdate = request.POST.get('reservationdate')
			reservationdate =  datetime.datetime.strptime(reservationdate.replace('-','/'),"%Y/%m/%d")
			reservationdate = datetime.datetime.strftime(reservationdate,'%y/%m/%d')
			selection = request.POST.get('reservationtimein')
			selection = reservationdate + '_' + selection
			scode, msg =formsub.book_a_reservation_confirm(patron,businessid,session,selection)
			if scode=='-1':
				context = {'msg' : msg, 'ngrok_address2' : ngrok_address}
				template = loader.get_template('NUS_dashboard_-1.html')
				return HttpResponse(template.render(context,request))
			elif scode =="1":
				context = {'msg' : msg, 'ngrok_address2' : ngrok_address, 'session' : session}
				template = loader.get_template('NUS_dashboard_1.html')
				return HttpResponse(template.render(context,request))
			while(1):
				session = random.randint(1000001,60000000000)
				check2=reservations.objects.filter(session=str(session))
				if check2:
					pass
				else:
					break;
		if 'option' in request.POST:
			session = request.POST.get('sessionid')
			businessid = request.POST.get('businessid')
			selection = request.POST.get('selection')
			#(2) Wednesday 04 November 2020 at 09:10
			time_indx = selection.index(':')
			time_selection = selection[time_indx-2:time_indx+3]
			date_indx = re.search("\d",selection[4:]).start(0)
			date_selection = selection[date_indx+4:time_indx-6]
			date_selection =  datetime.datetime.strptime(date_selection,"%d %B %Y")
			date_selection = datetime.datetime.strftime(date_selection,'%y/%m/%d')
			selection = date_selection + '_' + time_selection
			scode, msg =formsub.book_a_reservation_confirm(patron,businessid,session,selection)
			if scode=='-1':
				context = {'msg' : msg, 'ngrok_address2' : ngrok_address}
				template = loader.get_template('NUS_dashboard_-1.html')
				return HttpResponse(template.render(context,request))
			elif scode =="1":
				context = {'msg' : msg, 'ngrok_address2' : ngrok_address, 'session' : session}
				template = loader.get_template('NUS_dashboard_1.html')
				return HttpResponse(template.render(context,request))
		if 'option2' in request.POST:
			session = request.POST.get('sessionid')
			businessid = request.POST.get('businessid')
			selection = request.POST.get('selection')
			#(2) Wednesday 04 November 2020 at 09:10
			time_indx = selection.index(':')
			time_selection = selection[time_indx-2:time_indx+3]
			date_indx = re.search("\d",selection[4:]).start(0)
			date_selection = selection[date_indx+4:time_indx-6]
			date_selection =  datetime.datetime.strptime(date_selection,"%d %B %Y")
			date_selection = datetime.datetime.strftime(date_selection,'%y/%m/%d')
			selection = date_selection + '_' + time_selection
			scode, msg =formsub.change_a_reservation_confirm(patron,businessid,session,selection)
			if scode=='-1':
				context = {'msg' : msg, 'ngrok_address2' : ngrok_address}
				template = loader.get_template('NUS_dashboard_-1.html')
				return HttpResponse(template.render(context,request))
			elif scode =="1":
				context = {'msg' : msg, 'ngrok_address2' : ngrok_address, 'session' : session}
				template = loader.get_template('NUS_dashboard_1.html')
				return HttpResponse(template.render(context,request))

	try:
		query = "SELECT * FROM nus_reservations as nus_r INNER JOIN nus_establishments as nus_e ON nus_r.establishment = nus_e.username WHERE nus_r.status != 'cancelled' AND nus_r.patron =  '%s'" % patron
		user_reservations_info = reservations.objects.raw(query)

		# database datetime have to be 2 digit years and according format e.g: 20/11/04_11:04
		future_reservations = [user for user in user_reservations_info if datetime.datetime.strptime('20%s' % user.time_in, "%Y/%m/%d_%H:%M") > datetime.datetime.now()]

		k = range(1,len(future_reservations)+1)
		mylist = zip(k , future_reservations)
	except Exception as e:
		print(e)
		pass
	template = loader.get_template('NUS_dashboard.html')
	return HttpResponse(template.render(locals(),request))

@login_required
def reservation(request):
	ngrok_address2 = ngrok_address
	user=request.user
	patron=user.social_auth.get(provider='facebook').uid
	today = datetime.date.today()
	d1 = today.strftime("%Y-%m-%d")
	try:
		query = "SELECT * FROM nus_reservations as nus_r INNER JOIN nus_establishments as nus_e ON nus_r.establishment = nus_e.username WHERE nus_r.status = 'cancelled' AND nus_r.patron =  '%s'" % patron
		user_reservations_info = reservations.objects.raw(query)
		past_reservations_info = [user for user in user_reservations_info if datetime.datetime.strptime('20%s' % user.time_in, "%Y/%m/%d_%H:%M") < datetime.datetime.now() or user.status == 'cancelled']
		k = range(1,len(past_reservations_info)+1)
		mylist = zip(k , past_reservations_info)
	except Exception as e:
		pass
	template = loader.get_template("tables.html")
	return HttpResponse(template.render(locals(),request))

@login_required
def map(request):
	ngrok_address2 = ngrok_address
	all_establishment_register = establishments.objects.all()
	context = {
	'all_establishment_register': all_establishment_register,
	}
	template = loader.get_template("map.html")
	return HttpResponse(template.render(locals(),request))

@login_required
def support(request):
	ngrok_address2 = ngrok_address
	template = loader.get_template("support.html")
	return HttpResponse(template.render(locals(),request))	

@login_required
def profile(request):
	ngrok_address2 = ngrok_address
	if request.method == 'POST':
		user_ids = request.POST.get('id')
		address = request.POST.get('address')
		city = request.POST.get('city')
		country = request.POST.get('country')
		postal = request.POST.get('postal')
		contact = request.POST.get('contact')
		patrons.objects.filter(username=user_ids).update(user_address=address,user_country=country, user_city=city, user_postal=postal, user_handphone=contact)
	user=request.user
	b = patrons.objects.get(username=user.social_auth.get(provider='facebook').uid)
	template = loader.get_template('profile.html')
	return HttpResponse(template.render(locals(),request))

# Create your views here.
def login(request):
	ngrok_address2=ngrok_address
	template = loader.get_template('login.html')
	return HttpResponse(template.render(locals(),request))

def home(request):
    return render(request, 'home.html')


#Hamsi
#Function: communicate between dialogflow and web page
@csrf_exempt
def webhook(request):
    # build a request object
    name = user_details['name']
    patron = user_details['patron']
    print(user_details['name'] + "helo")
    req = json.loads(request.body)
    #dc.intent_info(req)
    # get action from json
    action = req.get('queryResult').get('action')
    fulfillmentText=''
    if action=='input.welcome':
        fulfillmentText = dc.input_welcome(req,patron,name)
    elif action=='get_clinic':
        fulfillmentText = dc.establishment_list(req,patron,'clinic')
    elif action=='get_shop':
        fulfillmentText = dc.establishment_list(req,patron,'shop')
    elif action=='get_restaurants':
        fulfillmentText = dc.establishment_list(req,patron,'restaurant')
        
    elif action=='book_reservation':
        fulfillmentText = dc.book_a_reservation(req, patron,name)
    elif action=='BookAReservation.BookAReservation-yes':
        fulfillmentText = dc.bookAReservation_yes(req, patron,name)
    elif action=='BookAReservation.BookAReservation-yes.BookAReservation-yes-custom-2':
        fulfillmentText = dc.bookAReservation_yes_bruleok02(req, patron,name) 
    elif action=='BookAReservation.BookAReservation-yes.BookAReservation-yes-custom-2.BookAReservation-yes-bruleok02-custom':
        fulfillmentText = dc.bookAReservation_yes_bruleok02_confirm(req, patron,name)     
        
    elif action=='BookAReservation.BookAReservation-yes.BookAReservation-yes-custom':
        fulfillmentText = dc.bookAReservation_yes_followup(req, patron,name)
        
    elif action=='cancel_reservation':
        fulfillmentText = dc.cancel_a_reservation(req, patron,name)
    elif action=='CancelAReservation.CancelAReservation-custom':
        fulfillmentText = dc.cancelAReservation_custom(req, patron, name)
    elif action=='CancelAReservation.CancelAReservation-custom.CancelAReservation-custom-yes':
        fulfillmentText = dc.cancelAReservation_custom_yes(req, patron, name)
        
        
    elif action=='change_by_date':
        fulfillmentText = dc.change_by_date(req, patron,name)
    elif action=='ChangeByDate.ChangeByDate-custom':
        fulfillmentText = dc.ChangeByDate_custom(req, patron, name)
    elif action=='ChangeByDate.ChangeByDate-custom.ChangeByDate-custom-yes':
        fulfillmentText = dc.ChangeByDate_custom_yes(req, patron, name)
    elif action=='ChangeByDate.ChangeByDate-custom.ChangeByDate-custom-yes.ChangeByDate-custom-yes-custom':
        fulfillmentText = dc.ChangeByDate_custom_yes_ok(req, patron, name)
    elif action=='ChangeByDate.ChangeByDate-custom.ChangeByDate-custom-yes.ChangeByDate-custom-yes-custom.ChangeByDate-custom-yes-ok-custom':
        print('b4')
        fulfillmentText = dc.ChangeByDate_custom_yes_ok_selectlist(req, patron, name)
    elif action=='ChangeByDate.ChangeByDate-custom.ChangeByDate-custom-yes.ChangeByDate-custom-yes-custom.ChangeByDate-custom-yes-ok-custom.ChangeByDate-custom-yes-ok-ok-custom':
        print('b5')
        fulfillmentText = dc.ChangeByDate_custom_yes_ok_selectlist_number(req, patron, name)    
    
    elif action=='checkReservation':
        fulfillmentText = dc.check_reservation(req, patron,name)
    
    elif action=='add_more_seats':
        fulfillmentText = dc.add_more_seats(req, patron,name)
    elif action=='reduce_seats':
        fulfillmentText = dc.reduce_seats(req, patron,name)
    
    
    
    elif action=='get_company_info':
        fulfillmentText = dc.about_company(req, patron,name)
    
    
    # elif action=='ReduceSeats.ReduceSeats-yes':
    #     fulfillmentText = dc.reduceSeats_yes(req, patron,name)
    # elif action=='AddMoreSeats.AddMoreSeats-yes':
    #     fulfillmentText = dc.addMoreSeats_yes(req, patron,name)
    
    # return response
    return JsonResponse(fulfillmentText, safe=False)
