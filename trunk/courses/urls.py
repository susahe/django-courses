from django.conf.urls.defaults import patterns, url
from courses import views

## TODO lesson edit

urlpatterns = patterns('',

    ### Temp ###
    url(r'^$', views.courses, name="course_list"),
    
    ### Course actions ###
    url(r'^create/$', views.course, name="course_create"),
    url(r'^(?P<course_slug>[-\w]+)/actions/edit/$', views.course, name="course_edit"),
    url(r'^(?P<course_slug>[-\w]+)/actions/(?P<action>activate|deactivate|reorder)/$', views.course_actions, name="course_actions"),
    url(r'^(?P<course_slug>[-\w]+)/actions/(?P<action>enroll|unenroll)/$', views.enrollment, name="course_enrollment"),        
    url(r'^(?P<course_slug>[-\w]+)/actions/add-lesson/$', views.lesson, name="course_lesson_create"),
    url(r'^(?P<course_slug>[-\w]+)/teachers/(?P<action>invite|remove)/$', views.teachership, name="course_teachership"),
    
    ### Course actions AJAX ###
    url(r'^(?P<course_slug>[-\w]+)/actions/(?P<action>activate|deactivate|reorder)/(?P<ajax>xml|json)/$', views.course_actions, name="course_actions_ajax"),
    url(r'^(?P<course_slug>[-\w]+)/actions/(?P<action>enroll|unenroll)/(?P<ajax>xml|json)/$', views.enrollment, name="course_enrollment_ajax"),        
    url(r'^(?P<course_slug>[-\w]+)/teachers/(?P<action>invite|remove)/(?P<ajax>xml|json)/$', views.teachership, name="course_teachership_ajax"),
    
    ### Teachership invitations and enrollment requests ###
    url(r'^requests/$', views.enrollment_requests, name="course_enrollment_request_list"),
    url(r'^requests/(?P<enrollment_request_uuid>[-\w]+)/(?P<action>accept|decline)/$', views.enrollment_response, name="course_enrollment_response"),
    url(r'^invitations/(?P<teachership_invitation_uuid>[-\w]+)/(?P<action>accept|decline)/$', views.teachership_response, name="course_teachership_response"),
    
    ### Teachership invitations and enrollment requests AJAX ### 
    url(r'^requests/(?P<enrollment_request_uuid>[-\w]+)/(?P<action>accept|decline)/(?P<ajax>xml|json)/$', views.enrollment_response, name="course_enrollment_response_ajax"),
    url(r'^invitations/(?P<teachership_invitation_uuid>[-\w]+)/(?P<action>accept|decline)/(?P<ajax>xml|json)/$', views.teachership_response, name="course_teachership_response_ajax"),
    
    ### Course detail ###
    url(r'^(?P<course_slug>[-\w]+)/$', views.course_detail, name="course_detail"),

    ### Lesson actions ###
    url(r'^(?P<course_slug>[-\w]+)/actions/add-lesson/(?P<ajax>xml|json)/$', views.lesson, name="course_lesson_create"),
    url(r'^(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/actions/edit/$', views.lesson, name="course_lesson_edit"),    
    url(r'^(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/actions/(?P<action>activate|deactivate)/$', views.lesson_actions, name="course_lesson_actions"),
    
    ### Lesson actions AJAX ###
    url(r'^(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/actions/(?P<action>activate|deactivate)/(?P<ajax>xml|json)/$', views.lesson_actions, name="course_lesson_actions_ajax"),

    ### Lesson detail ###
    url(r'^(?P<course_slug>[-\w]+)/(?P<lesson_slug>[-\w]+)/$', views.lesson_detail, name="course_lesson_detail"),


)
