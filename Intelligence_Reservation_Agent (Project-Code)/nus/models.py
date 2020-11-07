from django.db import models

# Create your models here.


# Create your models here.
class business_register(models.Model):
    business_id = models.CharField(max_length=50,default="SOME STRING")
    business_email = models.CharField(max_length=50,default="SOME STRING")
    business_incharge_person = models.CharField(max_length=50,default="SOME STRING")
    business_password = models.CharField(max_length=50,default="SOME STRING")
    business_contact = models.CharField(max_length=50,blank=True, null=True)
    business_mail_address = models.CharField(max_length=50,blank=True, null=True)
    def __str__(self):
        return self.business_id + self.business_email

####################################################################################################

class patrons(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.TextField(max_length=50) #uniqueidnumber
    email = models.TextField(max_length=50,default="-") #email address
    first_name = models.TextField(max_length=50,default="-")
    second_name = models.TextField(max_length=50,default="-")
    user_address = models.TextField(max_length=300,blank=True,null=True)
    user_country = models.TextField(max_length=50,blank=True,null=True)
    user_city = models.TextField(max_length=50,blank=True,null=True)
    user_postal = models.TextField(max_length=20,blank=True,null=True)
    user_handphone = models.TextField(max_length=50,blank=True,null=True)
    def __str__(self):
        return self.username

class establishments(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.TextField(max_length=50,default="-")
    username = models.TextField(max_length=50,default="-") #uniqueID
    company = models.TextField(max_length=100,default="-")
    location = models.TextField(max_length=100,default="-")
    type_business = models.TextField(max_length=50,default="-")
    contact = models.TextField(max_length=50,default="-")
    sublocs = models.TextField(max_length=100,default="-")
    max_cap = models.IntegerField()
    open_days = models.TextField(max_length=50)
    open_time = models.TextField(max_length=50)
    close_time = models.TextField(max_length=50)
    default_duration = models.IntegerField()
    days_in_advance = models.IntegerField(default="-")
    max_group_size = models.IntegerField()
    report_period = models.IntegerField(default='14')
    is_reminder = models.BooleanField(default=True)
    def __str__(self):
        return self.username

class reservations(models.Model):
    id = models.AutoField(primary_key=True)
    session = models.TextField(max_length=50)
    timestamp = models.TextField(max_length=50)
    patron = models.TextField(max_length=50)
    establishment = models.TextField(max_length=50)
    n_person = models.TextField(max_length=50)
    time_in = models.TextField(max_length=50)
    time_out = models.TextField(max_length=50)
    intent = models.TextField(max_length=50)
    status = models.TextField(max_length=50,default="-")
    loc = models.TextField(max_length=50,default="-")
    def __str__(self):
        return self.timestamp

class queries(models.Model):
    id = models.AutoField(primary_key=True)
    session = models.TextField(max_length=50)
    timestamp = models.TextField(max_length=50)
    patron = models.TextField(max_length=50) #
    establishment = models.TextField(max_length=50) #unique iD of business = username in establishment
    n_person = models.TextField(max_length=50)
    time_in = models.TextField(max_length=50)
    time_out = models.TextField(max_length=50)
    intent = models.TextField(max_length=50)
    step = models.TextField(max_length=50,default="-")
    action = models.TextField(max_length=50,default="-")
    selection = models.TextField(max_length=50,default="-")
    def __str__(self):
        return self.time_in + self.timestamp

class rsv_report(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.TextField(max_length=50)
    establishment = models.TextField(max_length=50)
    hourly  = models.TextField(max_length=1000)
    utilization = models.TextField(max_length=50)
    acceptance = models.TextField(max_length=50)
    source = models.TextField(max_length=50)
    period = models.TextField(max_length=50)

class qry_report(models.Model):
    id = models.AutoField(primary_key=True)
    establishment = models.TextField(max_length=50)
    timestamp = models.TextField(max_length=50)
    period  = models.TextField(max_length=50)
    n_total = models.TextField(max_length=50)
    DuplicateExist = models.TextField(max_length=50)
    FinalizeReservation = models.TextField(max_length=50)
    OfferSlots = models.TextField(max_length=50)
    OversizedGroup = models.TextField(max_length=50)
    PlaceNotAvail = models.TextField(max_length=50)
    OutsideOpenDays = models.TextField(max_length=50)
    InThePast = models.TextField(max_length=50)
    OnHoldReservation = models.TextField(max_length=50)
    TooSoon = models.TextField(max_length=50)

#class qry_report(models.Model):
#id timestamp establishment hourly utilization acceptance source period