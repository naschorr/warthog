"""Root conftest for the test suite.

Adds the ``test/replay/`` directory to ``sys.path`` so that shared helpers in
``test/replay/common/`` can be imported as
``from common.replay_test_helpers import …`` without colliding with the
stdlib ``test`` package.
"""

import sys
from pathlib import Path

# Allow ``from common.<module> import …`` inside any replay test file.
_replay_dir = str(Path(__file__).resolve().parent / "replay")
if _replay_dir not in sys.path:
    sys.path.insert(0, _replay_dir)
