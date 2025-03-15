import os

from .Util import Util
from .Logging import Logger
from .Context import Context
from .Context import OsTypes
from .Paths import Paths

class ServiceFileConfigPathPair:
    def __init__(self, serviceFileName, moonrakerConfigPath) -> None:
        self.ServiceFileName = serviceFileName
        self.MoonrakerConfigFilePath = moonrakerConfigPath

class Discovery:

    def FindTargetMoonrakerFiles(self, context: Context):
        Logger.Debug("Starting discovery.")
        self._PrintDebugPaths(context)

        if context.MoonrakerConfigFilePath is not None:
            if os.path.exists(context.MoonrakerConfigFilePath):
                if context.MoonrakerServiceFileName is not None and len(context.MoonrakerServiceFileName) > 0:
                    Logger.Debug(f"Installer script was passed a valid Moonraker config and service name. [{context.MoonrakerServiceFileName}:{context.MoonrakerConfigFilePath}]")
                    return

        pairList = self._FindAllServiceFilesAndPairings()

        if pairList is None or len(pairList) == 0:
            raise Exception("No moonraker instances could be detected on this device.")

        if context.MoonrakerConfigFilePath is not None:
            for p in pairList:
                if p.MoonrakerConfigFilePath == context.MoonrakerConfigFilePath:
                    context.MoonrakerServiceFileName = p.ServiceFileName
                    Logger.Debug(f"The given moonraker config was found with a service file pair. [{context.MoonrakerServiceFileName}:{context.MoonrakerConfigFilePath}]")
                    return
            Logger.Warn(f"Moonraker config path [{context.MoonrakerConfigFilePath}] was given, but no found pair matched it.")

        if len(pairList) == 1 and context.DisableAutoMoonrakerInstanceSelection is False:
            context.MoonrakerConfigFilePath = pairList[0].MoonrakerConfigFilePath
            context.MoonrakerServiceFileName = pairList[0].ServiceFileName
            Logger.Debug(f"Only one moonraker instance was found, so we are using it! [{context.MoonrakerServiceFileName}:{context.MoonrakerConfigFilePath}]")
            return

        Logger.Blank()
        Logger.Blank()
        Logger.Warn("Multiple Moonraker instances found.")
        Logger.Blank()

        count = 0
        for p in pairList:
            count += 1
            Logger.Info(F"  {str(count)}) {p.ServiceFileName} [{p.MoonrakerConfigFilePath}]")
        Logger.Blank()

    def _FindAllServiceFilesAndPairings(self) -> list:
        serviceFiles = self._FindAllFiles(Paths.SystemdServiceFilePath, "moonraker", ".service")
        results = []
        for f in serviceFiles:
            moonrakerConfigPath = self._TryToFindMatchingMoonrakerConfig(f)
            if moonrakerConfigPath is None:
                Logger.Debug(f"Moonraker config file not found for service file [{f}]")
            else:
                Logger.Debug(f"Moonraker service [{f}] matched to [{moonrakerConfigPath}]")
                results.append(ServiceFileConfigPathPair(os.path.basename(f), moonrakerConfigPath))
        return results

    def _TryToFindMatchingMoonrakerConfig(self, serviceFilePath: str) -> str or None:
        try:
            Logger.Debug(f"Searching for moonraker config for {serviceFilePath}")
            fixed_moonraker_path = "/usr/share/moonraker/moonraker.conf"
            if os.path.exists(fixed_moonraker_path):
                Logger.Debug(f"Moonraker config found at fixed path: {fixed_moonraker_path}")
                return fixed_moonraker_path

            with open(serviceFilePath, "r", encoding="utf-8") as serviceFile:
                lines = serviceFile.readlines()
                for l in lines:
                    if "moonraker.conf" in l.lower():
                        Logger.Debug("Found possible path line: " + l)
                        testPath = l.split('=')[-1].strip()
                        moonrakerConfigFilePath = self._FindMoonrakerConfigFromPath(testPath)
                        if moonrakerConfigFilePath:
                            return moonrakerConfigFilePath
            Logger.Debug("No matching config file found in service file, looking for more lines...")
        except Exception as e:
            Logger.Warn(f"Failed to read service config file: {serviceFilePath} {str(e)}")
        return None
    
    def _FindMoonrakerConfigFromPath(self, path, depth=0):
        if depth > 20:
            return None
        fixed_moonraker_path = "/usr/share/moonraker/moonraker.conf"
        if os.path.exists(fixed_moonraker_path):
            return fixed_moonraker_path
        try:
            fileAndDirList = os.listdir(path)
            for fileOrDirName in fileAndDirList:
                fullFileOrDirPath = os.path.join(path, fileOrDirName)
                if os.path.isfile(fullFileOrDirPath) and fileOrDirName.lower() == "moonraker.conf":
                    return fullFileOrDirPath
        except Exception as e:
            Logger.Debug(f"Failed to _FindMoonrakerConfigFromPath from path {path}: {str(e)}")
        return None

    def _FindAllFiles(self, path:str, prefix:str = None, suffix:str = None, depth:int = 0):
        results = []
        if depth > 10:
            return results
        fileAndDirList = sorted(os.listdir(path))
        for fileOrDirName in fileAndDirList:
            fullFileOrDirPath = os.path.join(path, fileOrDirName)
            if os.path.isdir(fullFileOrDirPath):
                tmp = self._FindAllFiles(fullFileOrDirPath, prefix, suffix, depth + 1)
                if tmp is not None:
                    results.extend(tmp)
            elif os.path.isfile(fullFileOrDirPath) and os.path.islink(fullFileOrDirPath) is False:
                include = prefix is None or fileOrDirName.lower().startswith(prefix)
                if include and suffix is not None:
                    include = fileOrDirName.lower().endswith(suffix)
                if include:
                    results.append(fullFileOrDirPath)
        return results


    def _PrintDebugPaths(self, context:Context):
        # Print all service files.
        Logger.Debug("Discovery - Service Files")
        self._PrintAllFilesAndSubFolders(Paths.GetServiceFileFolderPath(context))

        # We want to print files that might be printer data folders or names of other folders on other systems.
        Logger.Blank()
        Logger.Debug("Discovery - Config Files In Home Path")
        if context.IsCrealityOs():
            if os.path.exists(Paths.CrealityOsUserDataPath_SonicPad):
                self._PrintAllFilesAndSubFolders(Paths.CrealityOsUserDataPath_SonicPad, ".conf")
            if os.path.exists(Paths.CrealityOsUserDataPath_K1):
                self._PrintAllFilesAndSubFolders(Paths.CrealityOsUserDataPath_K1, ".conf")
        else:
            self._PrintAllFilesAndSubFolders(context.UserHomePath, ".conf")



    def _PrintAllFilesAndSubFolders(self, path:str, targetSuffix:str = None, depth = 0, depthStr = " "):
        if depth > 5:
            return
        # Use sorted, so the results are in a nice user presentable order.
        fileAndDirList = sorted(os.listdir(path))
        for fileOrDirName in fileAndDirList:
            fullFileOrDirPath = os.path.join(path, fileOrDirName)
            # Print the file or folder if it starts with the target suffix.
            if targetSuffix is None or fileOrDirName.lower().endswith(targetSuffix):
                Logger.Debug(f"{depthStr}{fullFileOrDirPath}")
            # Look through child folders.
            if os.path.isdir(fullFileOrDirPath):
                self._PrintAllFilesAndSubFolders(fullFileOrDirPath, targetSuffix, depth + 1, depthStr + "  ")
