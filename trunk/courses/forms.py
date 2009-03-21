from django.forms import ModelForm
from models import Course, Lesson


class CourseForm(ModelForm): 
    class Meta:
        model = Course
        fields = ('title', 'description', 'privacy', 'moderated')


class LessonForm(ModelForm):   
    class Meta:
        model = Lesson
        fields = ('title', 'description',)
