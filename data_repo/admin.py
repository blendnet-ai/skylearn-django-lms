from django.contrib import admin

from data_repo.models import QuestionBank, ConfigMap

class QuestionBankAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_preview', 'type', 'is_active', 'response_timelimit', 'updated_at']
    list_filter = ['is_active', ]
    
class ConfigMapAdmin(admin.ModelAdmin):
    list_display = ['id', 'tag', 'config', 'updated_at', 'is_active']
    list_filter = ['is_active', 'tag']

admin.site.register(QuestionBank, QuestionBankAdmin)
admin.site.register(ConfigMap, ConfigMapAdmin)
