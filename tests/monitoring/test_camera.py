import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../src'))

from monitoring.camera import CameraService

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
        self.assertEqual(self.service.selected_index, 0)
        
    @patch('cv2.VideoCapture')
    def test_start_fail(self, mock_videocapture):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_videocapture.return_value = mock_cap
        
        result = self.service.start()
        
        self.assertFalse(result)
        self.assertFalse(self.service.is_running())
        self.assertIsNone(self.service.cap)
        self.assertEqual(
            [call.args[0] for call in mock_videocapture.call_args_list],
            [0, 1, 2],
        )
        self.assertEqual(mock_cap.release.call_count, 3)

    @patch('cv2.VideoCapture')
    def test_start_uses_first_available_fallback_without_duplicates(
        self, mock_videocapture
    ):
        unavailable = MagicMock()
        unavailable.isOpened.return_value = False
        available = MagicMock()
        available.isOpened.return_value = True
        available.get.return_value = 0
        mock_videocapture.side_effect = [unavailable, available]

        service = CameraService(camera_index=0, fallback_indices=(0, 1, 2))
        self.assertTrue(service.start())

        self.assertEqual(service.selected_index, 1)
        self.assertEqual(
            [call.args[0] for call in mock_videocapture.call_args_list], [0, 1]
        )
        unavailable.release.assert_called_once()

    @patch('cv2.VideoCapture')
    def test_start_does_not_open_second_capture_when_running(
        self, mock_videocapture
    ):
        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.get.return_value = 0
        mock_videocapture.return_value = capture

        self.assertTrue(self.service.start())
        self.assertTrue(self.service.start())

        mock_videocapture.assert_called_once_with(0)
        
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
