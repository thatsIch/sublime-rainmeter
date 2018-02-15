"""Module for getting Rainmeter-specific paths."""

import os
import re
import filecmp
import ctypes

# own dependencies
from . import logger

from .path.program_path_provider import get_cached_program_path
from .path.setting_path_provider import get_cached_setting_path
from .path.program_drive_provider import get_cached_program_drive
from .path.plugin_path_provider import get_cached_plugin_path
from .path.addon_path_provider import get_cached_addon_path
from .path.skin_path_provider import get_cached_skin_path


def get_current_path(filepath):
    """Get the value of the #CURRENTPATH# variable for the specified path.

    Returns None if the file path is not in the skins folder
    """
    filepath = os.path.normpath(filepath)

    skinspath = get_cached_skin_path()
    if not skinspath or not filepath.startswith(skinspath):
        logger.info("current path could not be found because" +
                    " either the skins path could not be found or the current file" +
                    " is not located in the skins path.")
        return

    if os.path.isfile(filepath):
        return os.path.dirname(filepath) + "\\"
    else:
        return filepath + "\\"


def get_root_config_path(filepath):
    """Get the value of the #ROOTCONFIGPATH# variable for the specified path.

    Returns None if the path is not in the skins folder
    """
    filepath = os.path.normpath(filepath)

    skinspath = get_cached_skin_path()
    if not skinspath or not filepath.startswith(skinspath):
        logger.info("root config path could not be found" +
                    " because either the skins path could not be found or the" +
                    " current file is not located in the skins path.")
        return

    relpath = os.path.relpath(filepath, skinspath)
    logger.info(os.path.join(skinspath, relpath.split("\\")[0]) + "\\")

    return os.path.join(skinspath, relpath.split("\\")[0]) + "\\"


def get_current_file(filepath):
    """Get the value of the #CURRENTFILE# variable for the specified path.

    Returns None if the path is not in the skins folder
    """
    filepath = os.path.normpath(filepath)

    skinspath = get_cached_skin_path()
    if not skinspath or not filepath.startswith(skinspath):
        logger.info("current file could not be found because" +
                    " either the skins path could not be found or the current" +
                    " file is not located in the skins path.")
        return

    if os.path.isfile(filepath):
        return os.path.basename(filepath)
    else:
        logger.info("specified path is not a file.")
        return


def get_current_config(filepath):
    """Get the value of the #CURRENTCONFIG# variable for the specified path.

    Returns None if the path is not in the skins folder
    """
    filepath = os.path.normpath(filepath)

    skinspath = get_cached_skin_path()
    if not skinspath:
        logger.info("current config could not be found" +
                    " because the skins path could not be found.")
        return
    if not filepath.startswith(skinspath):
        logger.info("current config could not be found" +
                    " because the current file is not located in the skins path.")

        """workaround for symlinks:
        It could exists a symlink in the rainmeter skins folder.
        Rainmeter detects it correctly but uses the name of the symlink
        for the config name."""

        logger.info("trying symlink detection to find the skin config.")
        skins = os.listdir(skinspath)

        for skin in skins:
            check = os.path.join(skinspath, skin)
            # 0x0400 is the attribute for reparse point https://msdn.microsoft.com/en-us/library/ee332330(VS.85).aspx
            symbolic = os.path.isdir(check) and (ctypes.windll.kernel32.GetFileAttributesW(str(check)) & 0x0400) > 0
            if symbolic:
                logger.info("detected a symbolic link '" + check + "' through reparse pointer in file attributes.")
                walked = os.walk(check)
                # we walk deeper here because there can also be sub configs hidden in folders like <config/subconfig/config.ini>
                # which results the config being <config/subconfig>
                # at this point <skin> is probably the <config/
                for root, dirs, files in walked:
                    for file in files:
                        probe = os.path.join(root, file)
                        if filecmp.cmp(probe, filepath):
                            config = os.path.relpath(root, skinspath)
                            logger.info("found same file '" + file + "'. Recreate interpreted config '" + config + "'.")

                            return config

                            # when we found the file, we need to reverse the path to detect the sub configs
                            # _, probe_path_and_file = os.path.splitdrive(probe)
                            # _, actual_path_and_file = os.path.splitdrive(filepath)
                            
                            # prime the algorithm to remove the files
                            # probe_path, _ = os.path.split(probe_path_and_file)
                            # actual_path, _ = os.path.split(actual_path_and_file)

                            # while 1:
                            #     probe_path, probe_folder = os.path.split(probe_path)
                            #     actual_path, actual_folder = os.path.split(actual_path)
                            #     if probe_folder != actual_folder:
                            #         logger.info("Found last not matching folder '" + probe_folder + "' with '" + actual_folder + "'")

                            #         directory = os.path.dirname(probe)

                                    
               
        return

    # before you get the whole path called from the skin D:\Documents\Rainmeter\Skins\test\test.ini
    if os.path.isfile(filepath):
        filepath = os.path.dirname(filepath)
    # after the file name is trimmed D:\Documents\Rainmeter\Skins\test

    # the result is the directory path minus the skin path
    # D:\Documents\Rainmeter\Skins\test minus D:\Documents\Rainmeter\Skins\test equals test
    # thus the config is called <test>
    return os.path.relpath(filepath, skinspath)


def get_resources_path(filepath):
    """Get the value of the #@# variable for the specified path.

    Returns None if the path is not in the skins folder
    """
    rfp = get_root_config_path(filepath)

    if not rfp:
        return
    logger.info(os.path.join(rfp, "@Resources") + "\\")
    return os.path.join(rfp, "@Resources") + "\\"


def replace_variables(string, filepath):
    """Replace Rainmeter built-in variables and Windows environment variables in string.

    Replaces occurrences of the following variables in the string:
    #CURRENTFILE#
    #CURRENTPATH#
    #ROOTCONFIGPATH#
    #CURRENTCONFIG#
    #@#
    #SKINSPATH#
    #SETTINGSPATH#
    #PROGRAMPATH#
    #PROGRAMDRIVE#
    #ADDONSPATH#
    #PLUGINSPATH#
    Any Windows environment variables (like %APPDATA%)
    filepath must be a skin file located in a subdirectory of the skins folder
    """
    variables = {
        # lambdas for lazy evaluation
        "#CURRENTFILE#": lambda: get_current_file(filepath),
        "#CURRENTPATH#": lambda: get_current_path(filepath),
        "#ROOTCONFIGPATH#": lambda: get_root_config_path(filepath),
        "#CURRENTCONFIG#": lambda: get_current_config(filepath),
        "#@#": lambda: get_resources_path(filepath),
        "#SKINSPATH#": get_cached_skin_path,
        "#SETTINGSPATH#": get_cached_setting_path,
        "#PROGRAMPATH#": get_cached_program_path,
        "#PROGRAMDRIVE#": get_cached_program_drive,
        "#ADDONSPATH#": get_cached_addon_path,
        "#PLUGINSPATH#": get_cached_plugin_path
    }

    pattern = re.compile("(?i)" + "|".join(list(variables.keys())))
    # replace Rainmeter variables
    repl = pattern.sub(lambda x: variables[x.group().upper()](),
                       string)
    # expand windows environment variables
    repl = os.path.expandvars(repl)
    return repl


def make_path(string, filepath):
    """Make the string into an absolute path of an existing file or folder.

    Replacing Rainmeter built-in variables relative to the file specified in
    filepath (see replace_variables()) will return None if the file or folder
    doesn't exist, or if string is None or empty.
    """
    if not string:
        return None

    repl = replace_variables(string, filepath)
    norm = os.path.normpath(repl)

    # For relative paths, try folder of current file first

    if not os.path.isabs(norm):
        curpath = get_current_path(filepath)
        if curpath:
            abso = os.path.join(curpath, norm)
        else:
            abso = os.path.join(os.path.dirname(filepath), norm)

        if os.path.exists(abso):
            return abso

        # if that doesn't work, try relative to skins path
        # (for #CURRENTCONFIG#)
        abso = os.path.join(get_cached_skin_path(), norm)
        if os.path.exists(abso):
            return abso
    # for absolute paths, try opening containing folder if file does not exist
    else:
        if os.path.exists(norm):
            return norm

        if os.path.exists(os.path.dirname(norm)):
            return os.path.dirname(norm)

    return
