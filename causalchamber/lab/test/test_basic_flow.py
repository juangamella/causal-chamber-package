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

# --------------------------------------------------------------------
# Test queue mode

"""
Unit tests for the causalchamber.lab module.

These tests interact with the actual API using test credentials.
"""

import unittest
import time
import tempfile
import pathlib
import os
import numpy as np
from causalchamber.lab.lab import Lab
from causalchamber.lab.exceptions import UserError

# Test credentials - these should be set as environment variables
USER = os.environ.get('TEST_USER', 'test_user')
PASSWORD = os.environ.get('TEST_PASSWORD', 'test_password')

class TestLabConnection(unittest.TestCase):
    """Test Lab connection initialization with credentials."""
    
    def test_connection_with_credentials_tuple(self):
        """Test starting a connection with credentials tuple."""
        rlab = Lab(credentials=(USER, PASSWORD), verbose=False)
        self.assertIsNotNone(rlab)
        
    def test_connection_with_wrong_credentials(self):
        """Test that wrong credentials raise a UserError with code 401."""
        with self.assertRaises(UserError) as context:
            Lab(credentials=("wrong_user", "wrong_password"), verbose=False)
        self.assertEqual(context.exception.code, 401)


class TestSubmissionAndDownload(unittest.TestCase):
    """Test experiment submission and data download (non-image dataset)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = "/tmp"# tempfile.mkdtemp()
        self.rlab = Lab(credentials=(USER, PASSWORD), verbose=False)
        self.chamber_id = 'tt-test-dumy'
        self.config = 'standard'
    
    def test_submission_and_download_workflow(self):
        """Test complete workflow: create, submit, poll, and download data."""
        
        # Step 2: Create an experiment
        protocol = self.rlab.new_experiment(
            chamber_id=self.chamber_id,
            config=self.config
        )
        
        # Add some instructions
        protocol.wait(milliseconds=2_000)
        protocol.measure(n=1)
        
        # Step 3: Submit the experiment
        experiment_id = protocol.submit(tag="test_submission")
        self.assertIsNotNone(experiment_id)
        self.assertIsInstance(experiment_id, str)
        
        # Step 4: Check experiment appears in get_experiments()
        experiments = self.rlab.get_experiments(verbose=False)
        experiment_ids = [exp['experiment_id'] for exp in experiments]
        self.assertIn(experiment_id, experiment_ids)
        
        # Step 6: Calling download_data on a non-finished experiment should raise UserError
        with self.assertRaises(UserError) as context:
            self.rlab.download_data(experiment_id, root=self.temp_dir, verbose=False)
        self.assertEqual(context.exception.code, 0)  # Code 0 for not finished
        
        # Step 7: Check initial status is RUNNING (or QUEUED)
        experiment = self.rlab.get_experiment(experiment_id)
        initial_status = experiment['status']
        self.assertIn(initial_status, ['RUNNING', 'QUEUED'])
        
        # Step 8: Poll until status is DONE
        max_wait = 300  # 5 minutes timeout
        poll_interval = 2  # seconds
        elapsed = 0
        
        while elapsed < max_wait:
            experiment = self.rlab.get_experiment(experiment_id)
            status = experiment['status']
            
            if status == 'DONE':
                break
            elif status == 'FAILED':
                self.fail(f"Experiment {experiment_id} failed")
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        self.assertEqual(status, 'DONE', f"Experiment did not complete in {max_wait} seconds")
        
        # Step 9: Download the data and load the dataframe

        # Calling with a non-existent root directory should raise an error
        with self.assertRaises(FileNotFoundError) as context:
            dataset = self.rlab.download_data(
                experiment_id,
                root='/non/existent/directory/123',
                verbose=False
            )
        # Call with the appropriate root directory
        dataset = self.rlab.download_data(
            experiment_id,
            root=self.temp_dir,
            verbose=False
        )
        df = dataset.dataframe
        
        # Step 10: Check that df has one row
        self.assertEqual(len(df), 1)
        
        # Step 11: Calling image_arrays on non-image dataset should raise NotImplementedError
        with self.assertRaises(NotImplementedError):
            _ = dataset.image_arrays
        
        # Step 12: Calling image_iterator on non-image dataset should raise NotImplementedError
        with self.assertRaises(NotImplementedError):
            _ = dataset.image_iterator


class TestSubmissionAndDownloadWithImages(unittest.TestCase):
    """Test experiment submission and data download (image dataset)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.rlab = Lab(credentials=(USER, PASSWORD), verbose=False)
        self.chamber_id = 'tt-test-dumy'
        self.config = 'camera'  # Assuming this config returns images
    
    def test_submission_and_download_with_images(self):
        """Test complete workflow with image dataset."""
        
        # Step 2: Create an experiment
        protocol = self.rlab.new_experiment(
            chamber_id=self.chamber_id,
            config=self.config
        )

        protocol.wait(milliseconds=1_000)
        protocol.measure(n=1)
        protocol.wait(milliseconds=1_000)
        protocol.measure(n=1)
        protocol.wait(milliseconds=1_000)
        protocol.measure(n=1)
        
        # Step 3: Submit the experiment
        experiment_id = protocol.submit(tag="test_submission_images")
        self.assertIsNotNone(experiment_id)
        
        # Step 4: Check experiment appears in get_experiments()
        experiments = self.rlab.get_experiments(verbose=False)
        experiment_ids = [exp['experiment_id'] for exp in experiments]
        self.assertIn(experiment_id, experiment_ids)
        
        # Step 6: Calling download_data on non-finished experiment should raise error
        with self.assertRaises(UserError):
            self.rlab.download_data(experiment_id, root=self.temp_dir, verbose=False)
        
        # Step 7: Check initial status is RUNNING (or QUEUED)
        experiment = self.rlab.get_experiment(experiment_id)
        initial_status = experiment['status']
        self.assertIn(initial_status, ['RUNNING', 'QUEUED'])
        
        # Step 8: Poll until status is DONE
        max_wait = 300  # 5 minutes timeout
        poll_interval = 2  # seconds
        elapsed = 0
        
        while elapsed < max_wait:
            experiment = self.rlab.get_experiment(experiment_id)
            status = experiment['status']
            
            if status == 'DONE':
                break
            elif status == 'FAILED':
                self.fail(f"Experiment {experiment_id} failed")
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        self.assertEqual(status, 'DONE', f"Experiment did not complete in {max_wait} seconds")
        
        # Step 9: Download the data
        dataset = self.rlab.download_data(
            experiment_id,
            root=self.temp_dir,
            verbose=False
        )
        
        df = dataset.dataframe
        image_arrays = dataset.image_arrays
        image_iterator = dataset.image_iterator
        
        # Step 10: Check dimensions
        self.assertEqual(len(df), 3, "DataFrame should have 3 rows")
        self.assertEqual(len(image_arrays), 3, "Should have 3 images")
        
        # Step 11: Test image iterator
        # Check that we can iterate through exactly 3 images
        # and that each matches the corresponding image in image_arrays
        iterator_images = []
        for i, img in enumerate(image_iterator):
            iterator_images.append(img)
            if i >= 2:  # Stop after 3rd image (indices 0, 1, 2)
                break
        
        self.assertEqual(len(iterator_images), 3, "Iterator should yield 3 images")
        
        # Check that iterator images match image_arrays
        for i in range(3):
            np.testing.assert_array_equal(
                iterator_images[i],
                image_arrays[i],
                err_msg=f"Image {i} from iterator doesn't match image_arrays[{i}]"
            )


class TestQueueFunctionality(unittest.TestCase):
    """Test queue retrieval and management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rlab = Lab(credentials=(USER, PASSWORD), verbose=False)
        self.chamber_id = 'tt-test-dumy'
        self.config = 'standard'
    
    def test_get_queue_shows_right_experiments(self):
        """Test that get_queue shows the correct experiments."""
        
        # Step 2-3: Create and submit 3 experiments
        experiment_ids = []
        for i in range(3):
            protocol = self.rlab.new_experiment(
                chamber_id=self.chamber_id,
                config=self.config
            )
            exp_id = protocol.submit(tag=f"test_queue_{i}")
            experiment_ids.append(exp_id)
            time.sleep(0.5)  # Small delay between submissions
        
        # Step 4: Get the queue
        queue = self.rlab.get_queue(chamber_id=self.chamber_id, verbose=False)
        
        # Get experiment IDs from queue
        queue_experiment_ids = [exp['experiment_id'] for exp in queue]
        
        # Check that at least the last two experiments are in the queue
        # The first one might already be running
        self.assertIn(experiment_ids[1], queue_experiment_ids,
                     "Second experiment should be in queue")
        self.assertIn(experiment_ids[2], queue_experiment_ids,
                     "Third experiment should be in queue")
        
        # If the first experiment is not in the queue, check its status is RUNNING
        if experiment_ids[0] not in queue_experiment_ids:
            first_exp = self.rlab.get_experiment(experiment_ids[0])
            self.assertEqual(first_exp['status'], 'RUNNING',
                           "First experiment should be RUNNING if not in queue")
        
        # Step 5: Check submitted_by field
        for exp in queue:
            if exp['experiment_id'] in experiment_ids:
                self.assertEqual(exp['user_id'], USER,
                               "user_id should match USER")
        
        # Step 6: Check chamber_id and config fields
        for exp in queue:
            if exp['experiment_id'] in experiment_ids:
                self.assertEqual(exp['chamber_id'], self.chamber_id,
                               f"chamber_id should be {self.chamber_id}")
                self.assertEqual(exp['config'], self.config,
                               f"config should be {self.config}")


class TestProtocolOperations(unittest.TestCase):
    """Test Protocol class operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rlab = Lab(credentials=(USER, PASSWORD), verbose=False)
        self.chamber_id = 'tt-test-dumy'
        self.config = 'standard'
    
    def test_protocol_properties(self):
        """Test Protocol properties."""
        protocol = self.rlab.new_experiment(
            chamber_id=self.chamber_id,
            config=self.config
        )
        
        self.assertEqual(protocol.chamber_id, self.chamber_id)
        self.assertEqual(protocol.config, self.config)
    
    def test_protocol_submit_with_tag(self):
        """Test submitting protocol with custom tag."""
        protocol = self.rlab.new_experiment(
            chamber_id=self.chamber_id,
            config=self.config
        )
        
        custom_tag = "my_custom_tag"
        experiment_id = protocol.submit(tag=custom_tag)
        
        # Verify the tag was set correctly
        experiment = self.rlab.get_experiment(experiment_id)
        self.assertEqual(experiment.get('tag'), custom_tag)
    
    def test_protocol_submit_with_invalid_tag(self):
        """Test that submitting with invalid tag type raises TypeError."""
        protocol = self.rlab.new_experiment(
            chamber_id=self.chamber_id,
            config=self.config
        )
        
        with self.assertRaises(TypeError):
            protocol.submit(tag=123)  # tag must be string or None


class TestExperimentCancellation(unittest.TestCase):
    """Test experiment cancellation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rlab = Lab(credentials=(USER, PASSWORD), verbose=False)
        self.chamber_id = 'tt-test-dumy'
        self.config = 'standard'
    
    def test_cancel_queued_experiment(self):
        """Test cancelling a queued experiment."""
        # Create and submit an experiment
        protocol = self.rlab.new_experiment(
            chamber_id=self.chamber_id,
            config=self.config
        )
        protocol.submit(tag="test_cancel")
        experiment_id = protocol.submit(tag="test_cancel-2")
        
        # Cancel the experiment
        result = self.rlab.cancel_experiment(experiment_id)
        
        # Verify cancellation
        self.assertIsNotNone(result)
        
        # Check that status is now CANCELED
        experiment = self.rlab.get_experiment(experiment_id)
        # Status might be CANCELED or still RUNNING if it started before cancel
        self.assertIn(experiment['status'], ['CANCELED'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

# Check starting an rlab connection with a credentials_file and credentials; the credentials are stored in global variables USER and PASSWORD

# Check that wrong credentials raise a UserError(401, ...)

# Test submission & download
# 1. Start a connection to the lab
# 2. Create an experiment for chambed_id = 'tt-test-dumy', config = 'standard', leave instructions to fill by me
# 3. Submit it 
# 4. Call rlab.get_experiments() -> experiment id should appear there
# 6. Calling rlab.download_data(experiment_id) should return a UserError with code 422
# 7. Call rlab.get_experiment(experiment_id)['id']['status'] should be 'RUNNING'
# 8. Poll until rlab.get_experiment(experiment_id)['id']['status'] returns 'DONE'
# 9. Download the data and load the dataframe (rlab.download_data(experiment_id).dataframe)
# 10. Check that df has one row
# 11. Calling dataset.image_arrays on a non-image dataset -> should raise NotImplementedError
# 12. Calling dataset.image_iterator on a non-image dataset -> should raise NotImplementedError

# Test submission & download with images
# 1. Start a connection to the lab
# 2. Create an experiment for chambed_id = 'tt-test-dumy', config = 'standard', leave instructions to fill by me
# 3. Submit it 
# 4. Call rlab.get_experiments() -> experiment id should appear there
# 6. Calling rlab.download_data(experiment_id) should return an error
# 7. Call rlab.get_experiment(experiment_id)['id']['status'] should be 'RUNNING'
# 8. Poll until rlab.get_experiment(experiment_id)['id']['status'] returns 'DONE'
# 9. Download the data = rlab.download_data(experiment_id) and load the dataframe (data.dataframe) and image_arrays (data.image_arrays) and image_iterator (data.image_iterators).
# 10. Df should have 3 rows, len(images_array) = 3
# 11. image iterator can be iterated until 3rd call. At the ith call, the returned array is exactly the same is image_arrays[i]


# Test that get_queue shows the right experiments
# 1. Start a connection to the lab
# 2. Create an experiment for chambed_id = 'tt-test-dumy', config = 'standard', leave instructions to fill by me
# 3. Submit it 3 times, storing each returned id in a list
# 4. Call rlab.get_queue(chamber_id = 'tt-test-dumy'). Get the experiment_ids (key ['id'] in the returned dictionary); the last two stored ids should be in there. If the first is not, its ['status'] should be 'RUNNING'.
# 5. The ['submitted_by'] field should be equal to USER
# 6. The ['chamber_id'] and ['config'] should be equal to 'tt-test-dumy' and 'standard'.


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
