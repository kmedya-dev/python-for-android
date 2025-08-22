"""Simple functions for checking dependency versions."""

import sys
from os.path import join

import packaging.version

from pythonforandroid.logger import info, warning
from pythonforandroid.util import BuildInterruptingException

# We only check the NDK major version
MIN_NDK_VERSION = 27
MAX_NDK_VERSION = 27  # can be increased later

# buildozer parses this
RECOMMENDED_NDK_VERSION = "28c"

NDK_DOWNLOAD_URL = "https://developer.android.com/ndk/downloads/"

# Important log messages
NEW_NDK_MESSAGE = "Newer NDKs may not be fully supported by p4a."
UNKNOWN_NDK_MESSAGE = "Could not determine NDK version, no source.properties in the NDK dir."
PARSE_ERROR_NDK_MESSAGE = "Could not parse $NDK_DIR/source.properties, not checking NDK version."
READ_ERROR_NDK_MESSAGE = "Unable to read the NDK version from the given directory {ndk_dir}."
ENSURE_RIGHT_NDK_MESSAGE = (
    "Make sure your NDK version is greater than {min_supported}. "
    "If you get build errors, download the recommended NDK {rec_version} from {ndk_url}."
)
NDK_LOWER_THAN_SUPPORTED_MESSAGE = (
    "The minimum supported NDK version is {min_supported}. "
    "You can download it from {ndk_url}."
)
UNSUPPORTED_NDK_API_FOR_ARMEABI_MESSAGE = (
    "Asked to build for armeabi architecture with API {req_ndk_api}, "
    "but API {max_ndk_api} or greater does not support armeabi."
)
CURRENT_NDK_VERSION_MESSAGE = "Found NDK version {ndk_version}"
RECOMMENDED_NDK_VERSION_MESSAGE = (
    "Maximum recommended NDK version is {recommended_ndk_version}, "
    "but newer versions may work."
)


def check_ndk_version(ndk_dir):
    """Check the NDK version and raise/warn accordingly."""
    ndk_version = read_ndk_version(ndk_dir)

    if ndk_version is None:
        warning(READ_ERROR_NDK_MESSAGE.format(ndk_dir=ndk_dir))
        warning(
            ENSURE_RIGHT_NDK_MESSAGE.format(
                min_supported=MIN_NDK_VERSION,
                rec_version=RECOMMENDED_NDK_VERSION,
                ndk_url=NDK_DOWNLOAD_URL,
            )
        )
        return

    # Mapping NDK minor → letter (17.1 → 17b etc.)
    minor_to_letter = {0: ""}
    minor_to_letter.update(
        {n + 1: chr(i) for n, i in enumerate(range(ord("b"), ord("b") + 25))}
    )
    string_version = f"{ndk_version.major}{minor_to_letter.get(ndk_version.minor, '')}"
    info(CURRENT_NDK_VERSION_MESSAGE.format(ndk_version=string_version))

    if ndk_version.major < MIN_NDK_VERSION:
        raise BuildInterruptingException(
            NDK_LOWER_THAN_SUPPORTED_MESSAGE.format(
                min_supported=MIN_NDK_VERSION, ndk_url=NDK_DOWNLOAD_URL
            ),
            instructions=(
                "Please download a supported NDK from {ndk_url}.\n"
                "*** The currently recommended NDK version is {rec_version} ***"
            ).format(
                ndk_url=NDK_DOWNLOAD_URL,
                rec_version=RECOMMENDED_NDK_VERSION,
            ),
        )
    elif ndk_version.major > MAX_NDK_VERSION:
        warning(
            RECOMMENDED_NDK_VERSION_MESSAGE.format(
                recommended_ndk_version=RECOMMENDED_NDK_VERSION
            )
        )
        warning(NEW_NDK_MESSAGE)


def read_ndk_version(ndk_dir):
    """Read the NDK version from source.properties if possible."""
    try:
        with open(join(ndk_dir, "source.properties")) as fileh:
            ndk_data = fileh.read()
    except IOError:
        info(UNKNOWN_NDK_MESSAGE)
        return

    for line in ndk_data.splitlines():
        if line.startswith("Pkg.Revision"):
            unparsed_ndk_version = line.split("=")[-1].strip()
            return packaging.version.parse(unparsed_ndk_version)

    info(PARSE_ERROR_NDK_MESSAGE)
    return


# --- Android Target API requirements (as of 2025) ---
MIN_TARGET_API = 30                 # Android 11, baseline secure
RECOMMENDED_TARGET_API = 34         # Android 14 (Play Store requirement 2025)
ARMEABI_MAX_TARGET_API = 21         # armeabi was removed after API 21

OLD_API_MESSAGE = (
    "Target APIs lower than 30 are no longer supported on Google Play. "
    "The Target API should usually be as high as possible."
)


def check_target_api(api, arch):
    """Warn if target API is too low."""
    if api >= ARMEABI_MAX_TARGET_API and arch == "armeabi":
        raise BuildInterruptingException(
            UNSUPPORTED_NDK_API_FOR_ARMEABI_MESSAGE.format(
                req_ndk_api=api, max_ndk_api=ARMEABI_MAX_TARGET_API
            ),
            instructions="Use --arch=armeabi-v7a instead.",
        )

    if api < MIN_TARGET_API:
        warning(f"Target API {api} < {MIN_TARGET_API}")
        warning(OLD_API_MESSAGE)


# --- NDK API levels ---
MIN_NDK_API = 21                    # Android 5.0, baseline
RECOMMENDED_NDK_API = 24            # Android 7.0, safe for SDL2 and most bootstraps
OLD_NDK_API_MESSAGE = f"NDK API less than {MIN_NDK_API} is not supported"
TARGET_NDK_API_GREATER_THAN_TARGET_API_MESSAGE = (
    "Target NDK API {ndk_api} is higher than the target Android API {android_api}."
)


def check_ndk_api(ndk_api, android_api):
    """Ensure NDK API is within supported range."""
    if ndk_api > android_api:
        raise BuildInterruptingException(
            TARGET_NDK_API_GREATER_THAN_TARGET_API_MESSAGE.format(
                ndk_api=ndk_api, android_api=android_api
            ),
            instructions="NDK API must be <= target Android API.",
        )
    if ndk_api < MIN_NDK_API:
        warning(OLD_NDK_API_MESSAGE)


# --- Python version ---
MIN_PYTHON_VERSION = packaging.version.Version("3.6")
CURRENT_PYTHON_VERSION = packaging.version.Version(
    f"{sys.version_info.major}.{sys.version_info.minor}"
)

PY2_ERROR_TEXT = (
    f"python-for-android no longer supports Python 2. "
    f"Upgrade to Python {MIN_PYTHON_VERSION} or higher."
)

PY_VERSION_ERROR_TEXT = (
    f"Your Python version {CURRENT_PYTHON_VERSION} is not supported, "
    f"please upgrade to {MIN_PYTHON_VERSION} or higher."
)


def check_python_version():
    """Check the current Python version."""
    if sys.version_info.major == 2:
        raise BuildInterruptingException(PY2_ERROR_TEXT)

    if CURRENT_PYTHON_VERSION < MIN_PYTHON_VERSION:
        raise BuildInterruptingException(PY_VERSION_ERROR_TEXT)


# --- Helper: print recommended versions ---
def print_recommendations():
    """Print recommended dependency versions."""
    print(f"Min supported NDK version: {MIN_NDK_VERSION}")
    print(f"Recommended NDK version: {RECOMMENDED_NDK_VERSION}")
    print(f"Min target API: {MIN_TARGET_API}")
    print(f"Recommended target API: {RECOMMENDED_TARGET_API}")
    print(f"Min NDK API: {MIN_NDK_API}")
    print(f"Recommended NDK API: {RECOMMENDED_NDK_API}")
