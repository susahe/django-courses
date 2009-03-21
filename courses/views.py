from datetime import datetime

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import get_app
from django.conf import settings

from courses.utils import JSONResponse, XMLResponse
from courses.models import Course, Enrollment, Teachership, Lesson, TeachingInvitation, EnrollmentRequest
from courses.forms import CourseForm, LessonForm

from friends.models import friend_set_for

try:
    notification = get_app("notification")
except ImproperlyConfigured:
    notification = None

ALLOW_USER_COURSE_CREATION = getattr(settings, 'ALLOW_USER_COURSE_CREATION', True)
ALLOW_TEACHER_PERMISSION_CASCADE = getattr(settings, 'ALLOW_TEACHER_PERMISSION_CASCADE', True)


def _basic_response(user, ajax=False, message="Success!", redirect="/"):
    if ajax == 'json':
        return JSONResponse({'result': message}, is_iterable=False)
    elif ajax == 'xml':
        return XMLResponse("<result>%s</result>" % message, is_iterable=False)
    else:
        user.message_set.create(message=message)
        return HttpResponseRedirect(redirect)

### Course-related methods ###
def courses(request):
    course_list = get_list_or_404(Course)
    return render_to_response("courses/courses/list.html", {
        "courses":  course_list
    }, context_instance=RequestContext(request))

def course_detail(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not (course.activated or request.user in course.active_teachers()):
        if request.user:
            request.user.message_set.create(message="The course you tried to access \
                is currently inactive so can only be seen by course teachers. \
                If you are a teacher of this course, please log in to view it.")
        else:
            pass #should set a session message
        return HttpResponseRedirect(reverse("course_list"))
        
    return render_to_response('courses/courses/course.html', {
        'course': course,
        'lesson': course.lesson_set.all(), 
        'is_teacher': request.user in course.active_teachers(),
        'is_student': request.user in course.active_students()
    }, context_instance=RequestContext(request))

@login_required
def course(request, course_slug=None):
    if not ALLOW_USER_COURSE_CREATION:
        request.user.message_set.create(message="Course creation has been \
            disabled")
        return HttpResponseRedirect(reverse("course_list"))
    if course_slug:
        course = get_object_or_404(Course, slug=course_slug)
        template = 'courses/courses/edit.html'
    else:
        course = None
        template = 'courses/courses/create.html'
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            if course:
                form.save()
                request.user.message_set.create(message="Course changes have \
                    been saved")
            else:
                if form.cleaned_data['privacy'] == u'E':
                    form.cleaned_data['moderated'] = True                
                course = form.save()
                t = Teachership(course=course, teacher=request.user, is_owner=True)
                t.save()
                request.user.message_set.create(message="Your course has been \
                    created. It will not be visible to other users until you \
                    activate it.")               
            return HttpResponseRedirect(course.get_absolute_url())
    
    form = CourseForm(instance=course)
    return render_to_response(template, {
        'form': form,
        'course': course
    }, context_instance=RequestContext(request))    

@login_required
def course_actions(request, course_slug, action, ajax=False):
    course = get_object_or_404(Course, slug=course_slug)   
    if not request.user in course.active_teachers():
        request.user.mesage_set.create(message="The course you tried to edit may only \
            be edited by its teachers. If you are a teacher of this course, \
            please log in to edit it.")
        return HttpResponseRedirect(reverse("acct_login"))
    if request.method == "POST":
        if action == "activate":
            course.activated = datetime.now()
            course.save()
            message = "This course has now been activated and so may be seen by users"
        elif action == "deactivate":
            course.activated = None
            course.save()
            message = "This course has been deactivated and so may no longer be seen by users"
        elif action == "reorder":
            positions = request.POST.getlist(u"lesson[]")
            for lesson in course.lesson_set.all():
                lesson.position = int(positions[lesson.position - 1])
                lesson.save()
            message = "Course lessons have been reordered"
        return _basic_response(user=request.user, ajax=ajax, message=message, 
            redirect=request.META.get('HTTP_REFERER', course.get_absolute_url()))
    else:
        return HttpResponseForbidden("This URI accepts the POST method only")

@login_required
def enrollment(request, course_slug, action, ajax=False):
    course = get_object_or_404(Course, slug=course_slug)
    if request.user in course.active_teachers():
        return _basic_response(user=request.user, ajax=ajax, 
            message="You may not enroll in a course which you teach", 
            redirect=request.META.get('HTTP_REFERER', course.get_absolute_url()))    
    if request.method == "POST":
        if action == "enroll":    
            if course.moderated:
                er = EnrollmentRequest(requestor=request.user, course=course, status="R")
                er.save()
                if notification:
                    notification.send(course.active_teachers(), "course_student_request",
                        {'creator': request.user,
                         'course': course,
                         'uuid': er.uuid,})
                message = "Your enrollment request has been sent" 
            else:
                course.enroll(request.user)
                message = "You are now enrolled in this course"
        elif action == "unenroll":
            course.unenroll(request.user)
            message = "You have been unenrolled from this course"
    else:
        return HttpResponseForbidden("This URI accepts the POST method only")

    return _basic_response(user=request.user, ajax=ajax, message=message, 
        redirect=request.META.get('HTTP_REFERER', reverse("course_list")))

@login_required
def enrollment_requests(request):
    # TODO really shouldn't need two SELECTs and a list comprehension to do this!
    er_list = EnrollmentRequest.objects.filter(
        course__in=[t.course for t in 
                    Teachership.objects.filter(teacher=request.user)]
    )
    return render_to_response("courses/requests/list.html", {
        'enrollment_requests': er_list
    }, context_instance=RequestContext(request))  

@login_required
def enrollment_response(request, enrollment_request_uuid, action, ajax=False):
    #TODO should require POST method 
    er = get_object_or_404(EnrollmentRequest, 
                           uuid=enrollment_request_uuid, 
                           status="R")
    if not request.user in er.course.active_teachers():
        return _basic_response(user=request.user, ajax=ajax, 
            message="Only teachers of the \"%s\" course may moderate its \
                enrollment. If you are a teacher please log in to continue." % \
                er.course, 
            redirect=reverse("acct_login"))
    if action == "accept":        
        er.course.enroll(er.requestor)
        er.status = "A"
        er.save()
        notice_type = "course_student_acceptance"
        message = "%(student)s is now enrolled in the \"%(course)s\" course" % \
            {'student': er.requestor, 'course': er.course}
    elif action == "decline":
        er.status = "D"
        notice_type = "course_student_rejection"
        message = "%(student)s's request to join the \"%(course)s\" course \
            has been declined" % {'student': er.requestor, 'course': er.course}        
    
    er.save()
    if notification:
        notification.send([er.requestor], notice_type, {"course": er.course})
    #TODO what happens if there is no HTTP_REFERER or notifications?
    return _basic_response(user=request.user, ajax=ajax, message=message, 
        redirect=request.META.get('HTTP_REFERER', reverse("notification_notices")))

@login_required
def teachership(request, course_slug, action, ajax=False):
    course = get_object_or_404(Course, slug=course_slug)
    if not request.user in course.active_teachers():
        return _basic_response(user=request.user, ajax=ajax, 
            message="That action may only be performed by teachers of the \"%s\" \
                course. If you are a teacher, please log in." % course, 
            redirect=reverse("acct_login"))
    if action == "remove":
        if request.method == 'POST':
            if len(course.active_teachers()) <= 1:
                message = "You may not remove yourself as a teacher as you are \
                    the only one left!" % course
            else:
                course.unappoint_teacher(request.user)
                message="You have been removed as a teacher of the \"%s\" course" % course
            return _basic_response(user=request.user, ajax=ajax, message=message, 
                redirect=request.META.get('HTTP_REFERER', course.get_absolute_url()))
        else:
            return HttpResponseForbidden("This URI accepts the POST method only")           
    elif action == "invite":
        if not (request.user in course.owners()) and not ALLOW_TEACHER_PERMISSION_CASCADE:
            return _basic_response(user=request.user, ajax=ajax, 
                message="Only course owners may invite other teachers", 
                redirect=request.META.get('HTTP_REFERER', course.get_absolute_url()))
        if request.method == "POST":
            teachers = User.objects.filter(pk__in=request.POST.getlist(u'teachers'))
            for teacher in teachers:                        
                i = TeachingInvitation(invitor=request.user, invitee=teacher, course=course, 
                    status="I")
                i.save()
            if notification:
                notification.send(teachers, "course_teacher_invitation", {
                    'creator': request.user,
                    'course': course,
                    'uuid': i.uuid
                })
            return _basic_response(user=request.user, ajax=ajax, 
                message="Your invitation has been sent", 
                redirect=request.META.get('HTTP_REFERER', course.get_absolute_url()))
        else:
            return render_to_response("courses/courses/invite_teacher.html", {
                'course': course,
                'friends': [friend for friend in 
                            friend_set_for(request.user) if not 
                            friend in course.active_teachers()]
            }, context_instance=RequestContext(request))

@login_required
def teachership_response(request, teachership_invitation_uuid, action, ajax=False):
    #TODO should require POST method
    ti = get_object_or_404(TeachingInvitation, uuid=teachership_invitation_uuid, invitee=request.user)
    if action == "accept":
        ti.course.appoint_teacher(request.user)
        ti.course.unenroll(request.user)
        ti.status = "A"
        notice_type = "course_teacher_acceptance"
        message = "You are now a teacher of the \"%s\" course" % ti.course
        redirect = request.META.get('HTTP_REFERER', ti.course.get_absolute_url())
    elif action == "decline":
        ti.status = "D"
        notice_type = "course_teacher_rejection"
        message = "You have rejected an offer to teach the \"%s\" course" % ti.course
        redirect = request.META.get('HTTP_REFERER', reverse("notification_notices"))
        
    ti.save()
    if notification:
        notification.send([ti.invitor], notice_type, {
            "invitee": request.user,
            "course": ti.course
        })
    return _basic_response(user=request.user, ajax=ajax, message=message, redirect=redirect)

### Lesson-related methods ###
def lesson_detail(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug)
    is_teacher = request.user in course.active_teachers()
    is_student = request.user in course.active_students()
    
    ACCESSIBLE = course.privacy == "P" or \
                (course.privacy == "R" and request.user)  or \
                (course.privacy == "E" and is_student)
                
    if (course.activated and ACCESSIBLE) or is_teacher: 
        lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)
        if not lesson.activated and not is_teacher:
            if request.user:
                request.user.message_set.create(message="This lesson has been deactivated \
                    by a teacher, probably for maintenance. Please check back later.")
            else: 
                pass #should set a session message
            return HttpResponseRedirect(reverse("course_list"))
        return render_to_response("courses/lessons/lesson.html", {
            "lesson": lesson,
            "is_teacher": is_teacher,
            "is_student": is_student
        }, context_instance=RequestContext(request))
    else:
        if not course.activated:
            request.user.message_set.create(message="This course is not yet active so can \
                only be seen by course teachers. If you are a teacher of this \
                course, please log in to view it.")
            return HttpResponseRedirect(reverse("acct_login"))
        elif not ACCESSIBLE:
            # TODO can check if user to make these messages more releveant and redirects more useful
            MESSAGE = {
                "R": "You must be a registered user to view the \"%s\" \
                    course. If you are registered, please log in to view it." % 
                    course,
                "E": "You must be logged in and enrolled in the \"%s\" \
                    course in order to view it. If you are enrolled, please \
                    log in. "% course}
            if request.user:
                request.user.message_set.create(message=MESSAGE[course.privacy])
            else: 
                pass #should set a session message 
            return HttpResponseRedirect(course.get_absolute_url())

@login_required
def lesson(request, course_slug, lesson_slug=None):
    course = get_object_or_404(Course, slug=course_slug)
    if not request.user in course.active_teachers():
        request.user.message_set.create(message="That action may only be performed by \
            teachers of the \"%s\" course. If you are a teacher please log in." % 
            course)
        return HttpResponseRedirect(reverse("acct_login"))
    if lesson_slug:
        lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)
        template = "courses/lessons/edit.html"
    else:
        lesson = Lesson(course=course)
        template = "courses/lessons/create.html"
    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            if lesson_slug:
                form.save()
                request.user.message_set.create(message="Lesson changes have \
                    been saved")
            else:
                lesson = form.save()
                request.user.message_set.create(message="Lesson has been added")  
            return HttpResponseRedirect(lesson.get_absolute_url())
    
    form = LessonForm(instance=lesson)
    return render_to_response(template, {
        'form': form,
        'course': course,
        'lesson': lesson
    }, context_instance=RequestContext(request))

@login_required
def lesson_actions(request, course_slug, lesson_slug, action, ajax=False):
    #TODO should be single query
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)
    if not request.user in course.active_teachers():
        return _basic_response(user=request.user, ajax=ajax, 
            message="This lesson may only be modified by teachers of the \"%s\" \
                course. If you are a teacher please log in." % course, 
            redirect=reverse("acct_login"))
    if request.method == "POST":
        if action == "activate":
            lesson.activated = datetime.now()
            message="This lesson has now been activated and so may be seen by users"
        elif action == "deactivate":
            lesson.activated = None
            message="This lesson has now been deactivated and so may no longer \
                be seen by users"
        lesson.save()
        return _basic_response(user=request.user, ajax=ajax, message=message, 
            redirect=request.META.get('HTTP_REFERER', lesson.get_absolute_url()))
    else:
        return HttpResponseForbidden("This URI only accepts the POST method")






