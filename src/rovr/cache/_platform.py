# this shouldn't be that necessary, but I (NSPC911) have a shitty Windows
# machine, which for some reason, leads to stupid slow calls, so this is
# just an example for caching platform

import contextlib
import os
import platform
from os import path
from time import perf_counter

from rovr.variables.maps import RovrVars

cache = RovrVars.ROVRCACHE

# check for cache first
if path.exists(path.join(cache, "no_cache_uname")):
    # ignore because of marking
    pass
elif path.exists(jsonpath := path.join(cache, "uname.json")):
    import json

    try:
        with open(jsonpath, "r") as f:
            _platform = json.load(f)
    except (json.JSONDecodeError, OSError):
        # if we cant read the cache, delete the file so it is regened next time
        with contextlib.suppress(OSError):
            os.remove(jsonpath)
        _platform = platform.uname()._asdict()

    # you cannot directly kwarg-expand the _platform dict because the processor
    # field is missing from `__init__`, so you have to do it manually
    _processor = _platform.get("processor", "")
    _platform = platform.uname_result(
        system=_platform["system"],
        node=_platform["node"],
        release=_platform["release"],
        version=_platform["version"],
        machine=_platform["machine"],
    )
    _platform.processor = _processor  # type: ignore  # noqa
    # then monkey patch
    platform.uname = lambda: _platform  # type: ignore  # noqa
else:
    # get platform info
    start = perf_counter()
    _platform = platform.uname()._asdict()
    end = perf_counter()

    try:
        # create cache dir if it doesn't exist
        os.makedirs(cache, exist_ok=True)
        if end - start < 0.1:
            # fast enough, caching will be a lot slower than this, so we can skip caching
            open(path.join(cache, "no_cache_uname"), "w").close()
        else:
            # save to json
            import json

            with open(path.join(cache, "uname.json"), "w") as f:
                json.dump(_platform, f)
    except OSError:
        # if we can't write to cache, just ignore it
        pass
