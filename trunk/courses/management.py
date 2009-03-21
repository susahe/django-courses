from django.db.models import signals, get_app
from django.core.exceptions import ImproperlyConfigured

from django.utils.translation import ugettext_noop as _

try:
    notification = get_app('notification')

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("course_teacher_invitation", _("Invitation to Teach"), _("someone has invited you to help teach a course"))
        notification.create_notice_type("course_teacher_acceptance", _("Accepted Offer to Teach"), _("someone has accepted your offer to help teach a course"))
        notification.create_notice_type("course_teacher_rejection", _("Declined Offer to Teach"), _("someone has declined your offer to help teach a course"))
        notification.create_notice_type("course_student_request", _("Request to Enroll"), _("someone has requested to enroll in a course that you teach"))
        notification.create_notice_type("course_student_acceptance", _("Accepted Request to Enroll"), _("your request to enroll in a course has been accepted"))
        notification.create_notice_type("course_student_rejection", _("Declined Request to Enroll"), _("your request to enroll in a course has been declined"))

    signals.post_syncdb.connect(create_notice_types, sender=notification) 
except ImproperlyConfigured:
    print "Skipping creation of NoticeTypes as notification app not found"