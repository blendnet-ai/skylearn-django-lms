from accounts.permissions import IsLoggedIn, IsSuperuser, firebase_drf_authentication
from accounts.serializers import EnrollStudentsInBatchSerializer
from accounts.usecases import BatchAllocationUsecase, CourseProviderUsecase
from course.models import Batch
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes, permission_classes
from accounts.authentication import FirebaseAuthentication

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
