from accounts.permissions import IsLoggedIn, IsSuperuser, firebase_drf_authentication,IsCourseProviderAdmin
from accounts.serializers import EnrollStudentsInBatchSerializer
from accounts.usecases import BatchAllocationUsecase, CourseProviderUsecase
from course.models import Batch
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes, permission_classes
from accounts.authentication import FirebaseAuthentication
from accounts.models import Student
from accounts.repositories import StudentRepository, LecturerRepository
from accounts.models import User

@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsSuperuser])
def enroll_students_in_batch(request):
    serializer = EnrollStudentsInBatchSerializer(data=request.data)
    if serializer.is_valid():
        try:
            enrolled_students, failed_to_enroll_studends = (
                BatchAllocationUsecase.enroll_students_in_batch(
                    serializer.validated_data["batch_id"],
                    serializer.validated_data["student_ids"],
                )
            )
            return Response(
                (
                    {
                        "enrolled_students": enrolled_students,
                        "failed_to_enroll_studends": failed_to_enroll_studends,
                    }
                ),
                status=status.HTTP_201_CREATED,
            )
        except Batch.DoesNotExist:
            return Response(
                {"error": "Batch does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_course_provider(request):
    user_id = request.user.id
    # user_id=7
    course_provider = CourseProviderUsecase.get_course_provider(user_id)
    if course_provider is not None:
        return Response(course_provider, status=status.HTTP_200_OK)
    else:
        return Response(
            {"error": "Course provider not found"}, status=status.HTTP_404_NOT_FOUND
        )

@api_view(["PUT"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def update_student_status(request, student_id):
    """Update student status (Active/Inactive)"""
    try:
        new_status = request.data.get('status')
        
        # Validate if status is a valid choice
        if new_status not in [Student.Status.ACTIVE, Student.Status.INACTIVE]:
            return Response(
                {"error": "Invalid status. Must be 0 (Active) or 1 (Inactive)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if new_status == Student.Status.ACTIVE:
            StudentRepository.mark_student_active(student_id)
            status_string = "Active"
        else:
            StudentRepository.mark_student_inactive(student_id)
            status_string = "Inactive"
            
        return Response({
            "message": "Student status updated successfully",
            "student_id": student_id,
            "new_status": status_string
        }, status=status.HTTP_200_OK)
        
    except Student.DoesNotExist:
        return Response(
            {"error": "Student not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdmin])
def get_lecturers_by_provider(request, course_provider_id):
    """Get all lecturers for a specific course provider"""
    try:
        lecturers = LecturerRepository.get_lecturers_by_course_provider_id(course_provider_id)
        return Response({
            "lecturers": list(lecturers),
            "total_count": len(lecturers)
        }, status=status.HTTP_200_OK)
    except (ValueError, User.DoesNotExist) as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

