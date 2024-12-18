from .models import NotificationTemplate

class NotificationTemplateRepository:
    @staticmethod
    def create_template(name, subject, body, template_type):
        """
        Create a new notification template
        """
        return NotificationTemplate.objects.create(
            name=name,
            subject=subject,
            body=body,
            template_type=template_type
        )

    @staticmethod
    def get_template_by_type(template_type):
        """
        Get a template by its type
        """
        try:
            return NotificationTemplate.objects.get(template_type=template_type)
        except NotificationTemplate.DoesNotExist:
            return None

    @staticmethod
    def update_template(template_type, **kwargs):
        """
        Update an existing template
        """
        return NotificationTemplate.objects.filter(template_type=template_type).update(**kwargs)