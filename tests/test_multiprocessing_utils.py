from unittest.mock import MagicMock, patch

import pytest

from rovr.functions.multiprocessing_utils import safe_path_process_pool


def test_safe_path_process_pool_waits_on_success() -> None:
    executor = MagicMock()
    with (
        patch(
            "rovr.functions.multiprocessing_utils.SafePathProcessPoolExecutor",
            return_value=executor,
        ) as executor_type,
        safe_path_process_pool(max_workers=2) as active_executor,
    ):
        assert active_executor is executor

    executor_type.assert_called_once_with(max_workers=2)
    executor.shutdown.assert_called_once_with(wait=True)


def test_safe_path_process_pool_cancels_on_error() -> None:
    executor = MagicMock()
    with (
        patch(
            "rovr.functions.multiprocessing_utils.SafePathProcessPoolExecutor",
            return_value=executor,
        ),
        pytest.raises(RuntimeError, match="cancelled"),
        safe_path_process_pool(max_workers=1),
    ):
        raise RuntimeError("cancelled")

    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
