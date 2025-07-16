from django.contrib import admin
from .models import User, Student
from .models import CourseProvider

admin.site.register(CourseProvider)



admin.site.register(User)
admin.site.register(Student)
