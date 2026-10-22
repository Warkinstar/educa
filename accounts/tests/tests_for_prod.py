"""Tests for production, to test redirect 301 code and follow to redirect"""
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import reverse
from rest_framework import status