from rest_framework import generics, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from courses.api.serializers import SubjectSerializer, CourseSerializer, CourseWithContentsSerializer
from courses.models import Subject, Course
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from courses.api.permissions import IsEnrolled


class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class SubjectDetailView(generics.RetrieveAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

'''
class CourseEnrollView(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        course = get_object_or_404(Course, pk=pk)
        course.students.add(request.user)
        return Response({"enrolled": True})
'''

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return Course.objects.all()
        return Course.objects.visible_to_students()

    @action(
        detail=True,
        methods=["post"],
        authentication_classes=[BasicAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def enroll(self, request, *args, **kwargs):
        from rest_framework import status
        course = get_object_or_404(Course, pk=self.kwargs.get(self.lookup_field, kwargs.get("pk")))
        if not (course.is_active and course.is_public):
            return Response(
                {"error": "Самозапись на закрытый или неактивный курс запрещена."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        course.students.add(request.user)
        return Response({"enrolled": True})

    @action(
        detail=True,
        methods=["get"],
        authentication_classes=[BasicAuthentication],
        permission_classes=[IsAuthenticated, IsEnrolled],
        serializer_class=CourseWithContentsSerializer,
    )
    def contents(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)




