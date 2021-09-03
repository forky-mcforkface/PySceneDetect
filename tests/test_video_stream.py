# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
""" PySceneDetect scenedetect.video_stream Tests

This file includes unit tests for the scenedetect.video_stream module, as well as the video
backends implemented in scenedetect.backends.  These tests enforce a consistent interface across
all supported backends, and verify that they are functionally equivalent where possible.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name

import math
from typing import Type
import os.path
# Third-Party Library Imports
import numpy
import pytest

from scenedetect.video_stream import VideoStream, VideoOpenFailure
from scenedetect.backends.opencv import VideoStreamCv2

##
## List of Required/TBD Test Cases
##

# TODO: Add checks that frame was decoded properly - compare against
# a set of hand-picked frames? Or just a few colour samples?

# TODO: Add test using image sequence.

# TODO: Corrupt a video file
#def test_corrupt_video(vs_type: Type[VideoStream], corrupt_vid_path):

# Accuracy a framerate is checked to for testing purposes.
FRAMERATE_TOLERANCE = 0.001
# Accuracy a time in milliseconds is checked to for testing purposes.
TIME_TOLERANCE_MS = 0.1


def calculate_frame_delta(frame_a, frame_b, roi=None) -> float:
    if roi:
        assert False # TODO
    assert frame_a.shape == frame_b.shape
    num_pixels = frame_a.shape[0] * frame_a.shape[1]
    return numpy.sum(numpy.abs(frame_b - frame_a)) / num_pixels


def get_absolute_path(relative_path: str) -> str:
    # type: (str) -> str
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError('Test video file (%s) must be present to run test case!' %
                                relative_path)
    return abs_path


class VideoParameters:

    def __init__(self, path: str, height: int, width: int, frame_rate: float, total_frames: int):
        self.path = path
        self.height = height
        self.width = width
        self.frame_rate = frame_rate
        self.total_frames = total_frames
        # TODO: Aspect ratio.


def get_test_video_params():
    # type: () -> str
    """Fixture for parameters of all videos."""
    return [
        VideoParameters(
            path=get_absolute_path("testvideo.mp4"),
            width=1280,
            height=720,
            frame_rate=29.97,
            total_frames=720),
        VideoParameters(
            path=get_absolute_path("goldeneye/goldeneye.mp4"),
            width=1280,
            height=544,
            frame_rate=23.976,
            total_frames=1980),
    ]


pytestmark = pytest.mark.parametrize("vs_type", [VideoStreamCv2])


@pytest.mark.parametrize("test_video", get_test_video_params())
class TestVideoStream:

    def test_basic_params(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        stream = vs_type(test_video.path)
        assert stream.frame_size == (test_video.width, test_video.height)
        assert stream.frame_rate == pytest.approx(test_video.frame_rate, FRAMERATE_TOLERANCE)
        assert stream.duration.get_frames() == test_video.total_frames

    def test_read(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        stream = vs_type(test_video.path)
        frame = stream.read().copy()
        # For now hard-code 3 channels/pixel for each test video
        assert frame.shape == (test_video.height, test_video.width, 3)
        assert stream.frame_number == 1
        frame_copy = stream.read(decode=True, advance=False)
        assert calculate_frame_delta(frame, frame_copy) == pytest.approx(0.0)


    def test_seek(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """ Test VideoManager seek method. """
        stream = vs_type(test_video.path)
        base_timecode = stream.base_timecode
        assert stream.position == base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        assert stream.frame_number == 0

        # New "identity" timecodes in PySceneDetect v1.0.
        stream.seek(0.0)
        assert stream.frame_number == 1
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)

        stream.seek(stream.base_timecode)
        assert stream.frame_number == 1
        assert stream.position == base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)

        with pytest.raises(ValueError):
            # Minimum seek number in *frames* is now 1! See above.
            stream.seek(0)

        # Ensure accuracy over the first hundred frames.
        stream.reset()

        for i in range(1, 100 + 1):
            assert stream.read() is not None
            assert stream.position == base_timecode + (i - 1)
            assert stream.position_ms == pytest.approx(1000.0 * (i - 1) / float(stream.frame_rate),
                                                       abs=TIME_TOLERANCE_MS)
            assert stream.frame_number == i
        stream.reset()

        stream.seek(200)
        # TODO: Fix FrameTimecode so this can just be +200.
        assert stream.position == base_timecode + 199
        assert stream.position_ms == pytest.approx(1000.0 * (199.0 / float(stream.frame_rate)),
                                                   abs=TIME_TOLERANCE_MS)
        assert stream.frame_number == 200
        print(stream.position_ms)
        print(stream.position)

        stream.read()
        assert stream.frame_number == 201
        assert stream.position == base_timecode + 200
        assert stream.position_ms == pytest.approx(1000.0 * (200.0 / float(stream.frame_rate)),
                                                   abs=TIME_TOLERANCE_MS)




#
# Tests which only iterate over VideoStream types:
#


def test_invalid_path(vs_type: Type[VideoStream]):
    with pytest.raises(IOError):
        _ = vs_type('this_path_should_not_exist.mp4')


def test_seek_invalid(vs_type: Type[VideoStream], test_video_file: str):
    stream = vs_type(test_video_file)

    with pytest.raises(ValueError):
        stream.seek(0)

    with pytest.raises(ValueError):
        stream.seek(-1)

    with pytest.raises(ValueError):
        stream.seek(-0.1)



def test_reset(vs_type: Type[VideoStream], test_video_file: str):
    stream = vs_type(test_video_file)

    assert stream.read() is not None
    assert stream.frame_number > 0
    stream.reset()
    assert stream.frame_number == 0

