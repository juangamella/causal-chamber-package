# MIT License

# Copyright (c) 2025 Causal Chamber GmbH

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



import unittest
from unittest.mock import patch, Mock
import tempfile
import os
import requests

from causalchamber.lab.api import API
from causalchamber.lab.exceptions import LabError, UserError

# --------------------------------------------------------------------
# Load test credentials from environment

USER = os.getenv('API_TEST_USER')
PASSWORD = os.getenv('API_TEST_PASSWORD')

# --------------------------------------------------------------------
# Test API initialization

# Just calls to lab.api.API.init with credentials vs. credentials_file

class TestAPIInitialization(unittest.TestCase):
    """Tests for API initialization with different credential methods"""
    
    def setUp(self):
        """Set up temporary credentials file for testing"""
        # Create a temporary credentials file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini')
        self.temp_file.write('[api_keys]\n')
        self.temp_file.write('user = test_user\n')
        self.temp_file.write('password = test_password\n')
        self.temp_file.close()
        
    def tearDown(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_init_with_credentials_file(self):
        """Test initializing API with credentials_file parameter"""
        api = API(credentials_file=self.temp_file.name)
        self.assertEqual(api._api_user, 'test_user')
        self.assertEqual(api._api_password, 'test_password')
        self.assertEqual(api.user_id, 'test_user')
    
    def test_init_with_credentials_tuple(self):
        """Test initializing API with credentials parameter"""
        api = API(credentials=('username', 'password'))
        self.assertEqual(api._api_user, 'username')
        self.assertEqual(api._api_password, 'password')
        self.assertEqual(api.user_id, 'username')
    
    def test_init_with_both_credentials_and_file(self):
        """Test that credentials parameter takes precedence over credentials_file"""
        api = API(
            credentials_file=self.temp_file.name,
            credentials=('priority_user', 'priority_pass')
        )
        self.assertEqual(api._api_user, 'priority_user')
        self.assertEqual(api._api_password, 'priority_pass')
    
    def test_init_with_neither_credentials_nor_file(self):
        """Test that ValueError is raised when neither parameter is provided"""
        with self.assertRaises(ValueError) as context:
            API()
        self.assertIn('Either credentials_file or credentials must be provided', str(context.exception))
    
    def test_init_with_custom_endpoint(self):
        """Test initializing API with custom endpoint"""
        api = API(credentials=('user', 'pass'), endpoint='https://custom.api.com/v1')
        self.assertEqual(api.endpoint, 'https://custom.api.com/v1')
    
    def test_init_with_nonexistent_file(self):
        """Test that FileNotFoundError is raised for nonexistent credentials file"""
        with self.assertRaises(FileNotFoundError) as context:
            API(credentials_file='nonexistent_file.ini')
        self.assertIn('No credentials file found', str(context.exception))



# Check that calling API.make_requests with a bad URL raises LabError(404, ...)
# Check that calling API.make_requests with a bad method raises LabError(404, ...)
# Check that calling API.make_requests to a non-existent endpoint raises LabError(000, ...)


# ---------------------------------
# Real-time connections

# As chamber_id, use 'tt-test-dumy'. As chamber configurations use 'standard' for observations and 'camera' for observations + images.

# Check starting a chamber connection with credentials_file, credentials, both and neither

# Check that wrong credentials raise a UserError(401, ...)

# Check that wrong chamber_id raises a UserError(403, ...)

# Submit some basic correct instructions

# Check that wrong instruction parameters raises a UserError(400, ...)

# (observations only) Check succesful flow -> chamber connection (use tt-test-dumy) -> submit some instructions -> submit a batch

# (images) Check succesful flow -> chamber connection (use tt-test-0001) -> submit some instructions -> submit a batch

# ---------------------------------
# Queue mode

# Check starting an rlab connection with a credentials_file and credentials

# Check that wrong credentials raise a UserError(401, ...)

# Submit a valid experiment

#   should appear in get_experiments

# Test that get_queue shows the right experiments

# Try calling dataset.image_arrays on a non-image dataset -> should raise NotImplementedError

# Try calling dataset.image_iterator on a non-image dataset -> should raise NotImplementedError

# Calling dataset.image_arrays on an image dataset -> should return the image list of length == len(dataset.dataframe)

# Iterating over dataset.image_iterator should yield exactly the same images as return in dataset.image_arrays (compare using np.all())

