import sys
import time
import subprocess
import threading
import multiprocessing

from octoeverywhere.compression import Compression

from .Util import Util
from .Logging import Logger
from .Context import Context, OsTypes

# A helper class to make sure the optional dependencies are installed, like zstandard and ffmpeg.
# Note that ideally all apt-get and pip installs should be done here, to prevent package lock conflicts.
class OptionalDepsInstaller:

    # If there's an installer thread, it will be stored here.
    _InstallThread = None

    # Tries to install zstandard and ffmpeg, but this won't fail if the install fails.
    # The PIP install can take quite a long time (20-30 seconds) so we run in async.
    @staticmethod
    def TryToInstallDepsAsync(context:Context) -> None:
        # Since the pip and apt install can take a long time, do the install process async.
        OptionalDepsInstaller._InstallThread = threading.Thread(target=OptionalDepsInstaller._InstallThread, args=(context,), daemon=True)
        OptionalDepsInstaller._InstallThread.start()


    @staticmethod
    def WaitForInstallToComplete(timeoutSec:float=10.0) -> None:
        # See if we started a thread.
        t = OptionalDepsInstaller._InstallThread
        if t is None:
            return

        # If we did, report and try to join it.
        # If this fails, it's no big deal, because the plugin runtime will also try to install zstandard.
        Logger.Info("Finishing install... this might take a moment...")
        try:
            t.join(timeout=timeoutSec)
        except Exception as e:
            Logger.Debug(f"Failed to join optional installer thread. {str(e)}")


    @staticmethod
    def _InstallThread(context:Context) -> None:
        # Try to install ffmpeg, this is required for RTSP streaming.
        OptionalDepsInstaller._DoFfmpegInstall(context)

        # Try to install zstandard, this is optional but recommended.
        OptionalDepsInstaller._InstallZStandard(context)


    @staticmethod
    def _InstallZStandard(context:Context) -> None:
        try:
            # We don't even try installing on K1 or SonicPad, we know it fail.
            if context.OsType == OsTypes.K1 or context.OsType == OsTypes.SonicPad:
                return

            # We don't try install zstandard on systems with 2 cores or less, since it's too much work and the OS most of the time
            # Can't support zstandard because there's no pre-made binary, it can't be built, and the install process will take too long.
            if multiprocessing.cpu_count() < Compression.ZStandardMinCoreCountForInstall:
                return

            # Try to install the system package, if possible. This might bring in a binary.
            # If this fails, the PY package might be able to still bring in a pre-built binary.
            Logger.Debug("Installing zstandard, this might take a moment...")
            startSec = time.time()
            (returnCode, stdOut, stdError) = Util.RunShellCommand("sudo apt-get install zstd -y", False)
            Logger.Debug(f"Zstandard apt install result. Code: {returnCode}, StdOut: {stdOut}, StdErr: {stdError}")

            # Now try to install the PY package.
            # NOTE: Use the same logic as we do in the Compression class.
            # Only allow blocking up to 20 seconds, so we don't hang the installer too long.
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', Compression.ZStandardPipPackageString], timeout=30.0, check=False, capture_output=True)
            Logger.Debug(f"Zstandard PIP install result. Code: {result.returncode}, StdOut: {result.stdout}, StdErr: {result.stderr}, Time: {time.time()-startSec}")

        except Exception as e:
            Logger.Debug(f"Error installing zstandard. {str(e)}")


    @staticmethod
    def _DoFfmpegInstall(context:Context) -> None:
        try:
            # We don't even try installing on K1 or SonicPad, we know it fail.
            if context.OsType == OsTypes.K1 or context.OsType == OsTypes.SonicPad:
                return

            # Try to install ffmpeg, this is required for RTSP streaming.
            Logger.Debug("Installing ffmpeg, this might take a moment...")
            startSec = time.time()
            (returnCode, stdOut, stdError) = Util.RunShellCommand("sudo apt-get install ffmpeg -y", False)
            # Report the status to the installer log.
            Logger.Debug(f"FFmpeg install result. Code: {returnCode}, StdOut: {stdOut}, StdErr: {stdError}, Time: {time.time()-startSec}")
        except Exception as e:
            Logger.Debug(f"Error installing ffmpeg. {str(e)}")
