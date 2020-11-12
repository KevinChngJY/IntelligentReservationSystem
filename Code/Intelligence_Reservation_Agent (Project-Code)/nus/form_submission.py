
from . import ira

book_reservation_intentInfo={}
def book_a_reservation(Patron,businessId,session_info,dt,dt2,no_of_seats,date_of_reservation):
     agent = ira.Agent(str(session_info), 'NewReservation',Patron, str(businessId),time_in=dt,time_out=dt2,n_person=str(no_of_seats))
     scode, msg, step = agent.check_rules() 
     return scode, msg

def book_a_reservation_confirm(Patron,businessId,session_info,dt):
     agent = ira.Agent(str(session_info), 'NewReservation',Patron,str(businessId),selection = dt)
     scode, msg, step = agent.check_rules() 
     return scode, msg

def change_a_reservation(Patron,businessId,session_info,time_in,n_person,orginal):
     scode, msg, step= ira.Agent(str(session_info),'ChangeReservation', Patron, str(businessId)).check_rules()
     response = ira.Agent(str(session_info), 'ChangeReservation', Patron, str(businessId), selection=orginal).check_rules()
     scode, msg, step= ira.Agent(str(session_info),'ChangeReservation', Patron, str(businessId), time_in=time_in, n_person=n_person).check_rules()
     return scode, msg

def change_a_reservation_confirm(Patron,businessId,session_info,dt):
     scode, msg, step = ira.Agent(str(session_info), 'ChangeReservation', Patron, str(businessId), selection=dt).check_rules()
     print(msg)
     return scode, msg

def cancel_a_reservation(Patron,businessId,session_info,selection):
  scode, msg, step= ira.Agent(str(session_info), 'CancelReservation', Patron, str(businessId)).check_rules()
  scode, msg, step = ira.Agent(str(session_info), 'CancelReservation', Patron, str(businessId), selection=selection).check_rules()
  return scode, msg

def GA_housekeeping():
  ira.HouseKeeping().genetic_algorithm_check(all_days=True)

def SL_housekeeping():
  ira.HouseKeeping().linear_check(all_days=True)

def summary_query():
  ira.HouseKeeping().summarize_query(plot=True)