import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

from infrastructure.camera_service import CameraService

class TestCameraService(unittest.TestCase):
    def setUp(self):
        self.service = CameraService()
        
    @patch('cv2.VideoCapture')
    def test_start_success(self, mock_videocapture):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_videocapture.return_value = mock_cap
        
        result = self.service.start()
        
        self.assertTrue(result)
        self.assertTrue(self.service.is_running())
        mock_videocapture.assert_called_once_with(0)
        
    @patch('cv2.VideoCapture')
    def test_start_fail(self, mock_videocapture):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_videocapture.return_value = mock_cap
        
        result = self.service.start()
        
        self.assertFalse(result)
        self.assertFalse(self.service.is_running())
        self.assertIsNone(self.service.cap)
        
    @patch('cv2.VideoCapture')
    def test_stop(self, mock_videocapture):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_videocapture.return_value = mock_cap
        
        self.service.start()
        self.service.stop()
        
        self.assertFalse(self.service.is_running())
        mock_cap.release.assert_called_once()
        self.assertIsNone(self.service.cap)
        
    @patch('cv2.VideoCapture')
    @patch('cv2.cvtColor')
    def test_get_frame_running(self, mock_cvtcolor, mock_videocapture):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_videocapture.return_value = mock_cap
        
        mock_cvtcolor.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        
        self.service.start()
        frame = self.service.get_frame()
        
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (480, 640, 3))
        
    def test_get_frame_not_running(self):
        frame = self.service.get_frame()
        self.assertIsNone(frame)

if __name__ == '__main__':
    unittest.main()
