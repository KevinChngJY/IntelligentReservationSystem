from django.conf.urls import url, include
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import dialogflow_communications
from . import communications_channel

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^reservation$', views.reservation, name='reservation'),
    url(r'^support$', views.support, name='support'),
    url(r'^map$', views.map, name='map'),
    url(r'^profile$', views.profile, name='profile'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout$', auth_views.LogoutView.as_view(), name='logout'),
    url(r'^home$', views.home, name='home'),
    url(r'^social-auth/', include('social_django.urls', namespace="nus")),
    url(r'^signup_business',views.signup,name='signup'),
    url(r'^login_business',views.login1_business,name='login1_business'),
    url(r'^business_dashboard3',views.business_dashboard3,name='business_dashboard3'),
    url(r'^business_dashboard2',views.business_dashboard2,name='business_dashboard2'),
    url(r'^business_dashboard',views.business_dashboard,name='business_dashboard'),
    url(r'^business_logout',views.business_logout,name='business_logout'),
    url(r'^business_registration',views.business_registration,name='business_registration'),
    url(r'^business_profile',views.business_profile,name='business_profile'),
    url(r'^business_support$', views.business_support, name='business_support'),
    url(r'^webhook/$', views.webhook, name='webhook'),
    path('webhook/', views.webhook, name='webhook'),
]
