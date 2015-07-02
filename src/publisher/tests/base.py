import os
from django.test import TestCase

class BaseCase(TestCase):
    this_dir = os.path.dirname(os.path.realpath(__file__))
