from django.contrib import admin

from models import Course, Lesson, Teachership, Enrollment

class CourseAdmin(admin.ModelAdmin):
    fields = ('title', 'description', 'moderated', 'privacy')

admin.site.register(Course, CourseAdmin)


class LessonAdmin(admin.ModelAdmin):
    fields = ('title', 'description', 'course')

admin.site.register(Lesson, LessonAdmin)


class TeachershipAdmin(admin.ModelAdmin):
    fields = ('teacher', 'course', 'is_active', 'is_owner')

admin.site.register(Teachership, TeachershipAdmin)


class EnrollmentAdmin(admin.ModelAdmin):
    fields = ('student', 'course', 'is_active')

admin.site.register(Enrollment, EnrollmentAdmin)

