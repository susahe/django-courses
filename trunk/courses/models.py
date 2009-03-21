from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from courses.utils import UUIDField, slugify

# TODO i18n of field names

class Course(models.Model):
    """
    A Course effectively serves as a collection of lesson objects with shared 
    properties such as subject matter, teachers, students and permissions.
    """
    PRIVACY_CHOICES = (
        ('P', 'Public'),
        ('R', 'Registered users only'),
        ('E', 'Enrolled students only'),
    )
    
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, db_index=True)
    teachers = models.ManyToManyField(User, 
                                      related_name='teachers', 
                                      through='Teachership')
    students = models.ManyToManyField(User, 
                                      related_name='students', 
                                      through='Enrollment')
    privacy = models.CharField(max_length=1, 
                               choices=PRIVACY_CHOICES, 
                               default='P',
                               help_text="This Defines who can see active lessons \
                                    in this course. 'Public' means that anybody \
                                    can see them, 'Registered users only' means \
                                    that those who are logged in to this site can \
                                    see them, and 'Enrolled students only' means \
                                    only those who enroll as students in this \
                                    course may see them.")
    moderated = models.BooleanField(default=False,
                                    help_text="If you select this setting, any \
                                        request by a student to enroll in this \
                                        course will need to be approved by a \
                                        course teacher.") 
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    activated = models.DateTimeField(null=True)
    
    class Meta:
        verbose_name = _('course')
        verbose_name_plural = _('courses')
        ordering = ['activated']
        
    def __unicode__(self):
        return self.title
        
    def save(self, force_insert=False, force_update=False):
        self.slug = slugify(self.title, 
                            invalid=("create", "invitations", "requests"), 
                            instance=self)
        super(Course, self).save(force_insert, force_update)
        
    def get_absolute_url(self):
        return "/courses/%s/" % self.slug
        
    def active_teachers(self):
        return self.teachers.filter(teachership__is_active=True)
        
    def active_students(self):
        return self.students.filter(enrollment__is_active=True)
        
    def owners(self):
        return self.teachers.filter(teachership__is_owner=True)
    
    # TODO the Course class probably isn't the most appropriate place 
    # for the following 4 methods
    def enroll(self, user):
        e, created = Enrollment.objects.get_or_create(course=self, student=user)
        if not created:
            e.is_active = True
            e.save()
        return created
    
    def unenroll(self, user):
        try:
            e = Enrollment.objects.get(course=self, student=user)
            e.is_active = False
            e.save()
            return True
        except Enrollment.DoesNotExist:
            return False
            
    def appoint_teacher(self, user):
        t, created = Teachership.objects.get_or_create(course=self, teacher=user)
        if not created:
            t.is_active = True
            t.save()
        return created
        
    def unappoint_teacher(self, user):
        try:
            t = Tearchership.objects.get(course=self, teacher=user)
            t.is_active = False
            t.save()
            return True
        except Teachership.DoesNotExist:
            return False
        

class Enrollment(models.Model):
    """
    An intermediary for the Course<->User m2m relation known as ``students``.
    
    This exists mostly for the purpose of the ``is_active`` attribute so that 
    course removal can be reverted in a straightforward manner. This is 
    particularly handy for paid enrollment where a student may voluntarily 
    unenroll but ought to be entitled to re-enroll at will.
    """
    student = models.ForeignKey(User)
    course = models.ForeignKey(Course)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('enrollment')
        verbose_name_plural = _('enrollments')
        unique_together = ('student', 'course')
    
    def __unicode__(self):
        return "%(student)s enrolled in the \"%(course)s\" course" % \
            {'student': self.student, 'course': self.course}


class EnrollmentRequest(models.Model):
    """
    A request by a user to become a student in a course with moderated enrollment
    """
    STATUS_CHOICES = (
        ('R', 'Requested'),
        ('A', 'Accepted'),
        ('D', 'Declined'),
    )
        
    uuid = UUIDField(primary_key=True, max_length=36)
    requestor = models.ForeignKey(User, related_name='requestor')
    course = models.ForeignKey(Course)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    
    class Meta:
        verbose_name = _('enrollment request')
        verbose_name_plural = _('enrollment requests')
            
    def __unicode__(self):
        return "%(requestor)s requested to join the \"%(course)s\" course" % \
            {'requestor': self.requestor, 'course': self.course}


class Teachership(models.Model):
    """
    An intermediary for Course<->User m2m relationship known as ``teachers``
    """
    teacher = models.ForeignKey(User)
    course = models.ForeignKey(Course)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_owner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('teachership')
        verbose_name_plural = _('teacherships')
        unique_together = ('teacher', 'course')
        
    def __unicode__(self):
        return "%(teacher)s teaching the \"%(course)s\" course" % \
            {'teacher': self.teacher, 'course': self.course}


class TeachingInvitation(models.Model):
    """
    An invitation by a course teacher to invite another user to teach
    """
    STATUS_CHOICES = (
        ('I', 'Invited'),
        ('A', 'Accepted'),
        ('D', 'Declined'),
    )
        
    uuid = UUIDField(primary_key=True, max_length=36)
    invitor = models.ForeignKey(User, related_name="invitor")
    invitee = models.ForeignKey(User, related_name="invitee")
    course = models.ForeignKey(Course)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
        
    class Meta:
        verbose_name = _('teaching invitation')
        verbose_name_plural = _('teaching invitations')
        unique_together = ('invitor', 'invitee', 'course')
        
    def __unicode__(self):
        return "%(invitee)s invited by %(invitor)s to teach the \"%(course)s\" \
            course" % {
            'invitee': self.invitee, 
            'invitor': self.invitor, 
            'course': self.course
        }


class Lesson(models.Model):
    """
    The basic unit of a course, with which content will be associated
    """
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, db_index=True)
    position = models.PositiveSmallIntegerField()
    course = models.ForeignKey(Course)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    activated = models.DateTimeField(null=True, auto_now_add=True)
    
    class Meta:
        verbose_name = _('lesson')
        verbose_name_plural = _('lessons')
        ordering = ['position']
        unique_together = ('course', 'position')
        
    def __unicode__(self):
        return self.title
        
    def save(self, force_insert=False, force_update=False):
        self.slug = slugify(self.title, 
                            instance=self, 
                            invalid=('actions', 'teachers'), 
                            extra_lookup={'course': self.course})
        if not self.position:
            self.position = len(Lesson.objects.filter(course=self.course)) + 1
        super(Lesson, self).save(force_insert, force_update)
        
    def get_absolute_url(self):
        return "/courses/%(cslug)s/%(lslug)s/" % \
            {'cslug': self.course.slug, 'lslug': self.slug}
        


