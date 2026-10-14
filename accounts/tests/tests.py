from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import reverse
from rest_framework import status