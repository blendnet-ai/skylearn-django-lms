class CourseContentDriveException(Exception):
    class InvalidFolderFormatException(Exception):
        def __init__(self, folder_name):
            super().__init__(f"Invalid folder format: {folder_name}")

    class CourseNotFoundException(Exception):
        def __init__(self, course_id):
            super().__init__(f"Course with code {course_id} not found in database")

    class ModuleNotFoundException(Exception):
        def __init__(self, module_id, course_id):
            super().__init__(f"Module with code {module_id} for course {course_id} not found in database")

    class DriveFileUploadException(Exception):
        def __init__(self, file_name, error):
            super().__init__(f"Failed to upload file {file_name}: {str(error)}")

    class DriveAPIException(Exception):
        def __init__(self, operation, error):
            super().__init__(f"Drive API {operation} failed: {str(error)}")
    
    class DriveInitializationException(Exception):
        def __init__(self, error):
            super().__init__(f"Failed to initialize Google Drive API: {str(error)}")

    class OrganizationProcessingException(Exception):
        def __init__(self, org_name, error):
            super().__init__(f"Failed to process organization {org_name}: {str(error)}")