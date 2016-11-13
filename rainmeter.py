"""Module for getting Rainmeter-specific paths"""

import os
import re
import io
import getpass
import platform
import winreg

import yaml
import inspect
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"completion")))

if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)  

os.chdir(dir_path)

from completion import Loader

import sublime
import sublime_plugin

def _log(function, string):
    if log:
        print("rainmeter." + function + ': ' + string)


def program_path():
    """Get the cached value of the #PROGRAMPATH# variable"""

    return _program_path


def program_drive():
    """Get the cached value of the #PROGRAMDRIVE# variable"""

    return _program_drive


def settings_path():
    """Get the cached value of the #SETTINGSPATH# variable"""

    return _settings_path


def skins_path():
    """Get the cached value of the #SKINSPATH# variable"""

    return _skins_path


def plugins_path():
    """Get the cached value of the #PLUGINSPATH# variable"""

    return _plugins_path


def addons_path():
    """Get the cached value of the #ADDONSPATH# variable"""

    return _addons_path


def get_program_path():
    """Get the value of the #PROGRAMPATH# variable"""

    # Load setting
    settings = sublime.load_settings("Rainmeter.sublime-settings")
    rainmeterpath = settings.get("rainmeter_path", None)

    # If setting is not set, try default location
    if not rainmeterpath:
        _log("get_program_path", "rainmeter_path not found in settings." +
             " Trying default location.")
        # Default: "C:\Program Files\Rainmeter"
        programfiles = os.getenv("PROGRAMFILES")
        rainmeterpath = os.path.join(programfiles, "Rainmeter") + "\\"

        # if it is not even specified by default, try using the registry to retrieve the installation path
        if not os.path.isdir(rainmeterpath):
            regkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\WOW6432Node\Rainmeter")
            keyval = winreg.QueryValueEx(regkey, "Personal")

            pathrep = keyval[0]
    
            for i in range(1024):
                try:
                    asubkey_name=EnumKey(keyval,i)
                    asubkey=OpenKey(keyval,asubkey_name)
                    val=QueryValueEx(asubkey, "DisplayName")
                    _log("test", val)
                except EnvironmentError:
                    break


    # normalize path
    rainmeterpath = os.path.normpath(rainmeterpath) + "\\"

    # Check if path exists and contains Rainmeter.exe
    if not os.path.exists(rainmeterpath + "Rainmeter.exe"):
        _log("get_program_path", "Path to Rainmeter.exe could not be" +
             " found. Check your \"rainmeter_path\" setting.")
        return

    _log("get_program_path", "Rainmeter found in " + rainmeterpath)
    return rainmeterpath


def get_program_drive():
    """Get the value of the #PROGRAMDRIVE# variable"""

    rainmeterpath = program_path()

    if not rainmeterpath:
        return

    if re.match("[a-zA-Z]:", rainmeterpath):
        return os.path.splitdrive(rainmeterpath)[0]

    if rainmeterpath.startswith(r"\\"):
        return os.path.splitunc(rainmeterpath)[0]

    return


def get_settings_path():
    """Get the value of the #SETTINGSPATH# variable"""

    rainmeterpath = program_path()

    if not rainmeterpath:
        return

    # Check if Rainmeter.ini is in Rainmeter program directory
    if os.path.exists(rainmeterpath + "Rainmeter.ini"):
        _log("get_settings_path", "Rainmeter.ini found in " + rainmeterpath)
        return rainmeterpath
    else:  # If not, look in %APPDATA%\Rainmeter\
        appdata = os.getenv("APPDATA")
        if os.path.exists(os.path.join(appdata, "Rainmeter\\Rainmeter.ini")):
            _log("get_settings_path", "Rainmeter.ini found in " +
                 os.path.join(appdata, "Rainmeter") + "\\")
            return os.path.join(appdata, "Rainmeter") + "\\"
        else:
            _log("get_settings_path", "Rainmeter.ini could not be located.")
            return None


def get_skins_path():
    """Get the value of the #SKINSPATH# variable"""

    # First try to load the value from the "rainmeter_skins_path" setting
    settings = sublime.load_settings("Rainmeter.sublime-settings")
    skinspath = settings.get("rainmeter_skins_path", None)

    # if it's found, return it
    # We trust the user to enter something meaningful here
    # and don't check anything.
    if skinspath:
        _log("get_skins_path", "Skins path found in sublime-settings file.")
        return os.path.normpath(skinspath) + "\\"

    # If it's not set, try to detect it automagically

    rainmeterpath = program_path()
    if not rainmeterpath:
        return

    settingspath = settings_path()
    if not settingspath:
        return

    # First, try to read the SkinPath setting from Rainmeter.ini
    fhnd = io.open(os.path.join(settingspath, "Rainmeter.ini"))
    lines = fhnd.read()
    fhnd.close()

    # Find the skinspath setting in the file
    match = re.search(r"""(?imsx)

                     # Find the first [Rainmeter] section
                     (^\s*\[\s*Rainmeter\s*\]\s*$)
                     (.*?

                         # Find the "SkinPath" and "="
                         (^\s*SkinPath\s*=\s*

                             # Read until the next line ending and store
                             # in named group
                             (?P<skinpath>[^$]+?)\s*?$
                         )
                     ).*?

                     # All of this needs to happen before the next section
                     (?:^\s*\[\s*[^\[\]\s]+\s*\]\s*$)
                     """, lines)

    # if skinspath setting was found, return it
    if match:
        _log("get_skins_path", "Skins path found in Rainmeter.ini.")
        return match.group("skinpath").strip().replace("/", "\\")

    # if it's not found in the settings file, try to guess it

    # If program path and setting path are equal, we have a portable
    # installation. In this case, the Skins folder is inside the rainmeter
    # path
    if os.path.samefile(rainmeterpath, settingspath):
        _log("get_skins_path", "Skin path found in #PROGRAMPATH#" +
             " because portable installation")
        return os.path.join(rainmeterpath, "Skins") + "\\"

    # If it's not a portable installation, we try looking into the "My
    # Documents" folder Since it could be relocated by the user, we have to
    # query its value from the registry
    try:
        regkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows" +
                                r"\CurrentVersion\Explorer" +
                                r"\User Shell Folders")
        keyval = winreg.QueryValueEx(regkey, "Personal")

        pathrep = keyval[0]

        # The path could (and most likely, will) contain environment
        # variables that have to be expanded first
        pathrep = os.path.expandvars(pathrep)

        _log("get_skins_path", "Guessed Skin path from My Documents" +
             " location in registry")
        return os.path.join(pathrep, "Rainmeter\\Skins") + "\\"

    except WindowsError:
        pass

    # If the value could not be retrieved from the registry,
    # we try some educated guesses about default locations
    try:
        username = getpass.getuser()
    except Exception:
        _log("get_skins_path", "Skins path could not be located." +
             " Please set the \"skins_path\" setting in your Rainmeter" +
             " settings file.")
        return
    else:
        mydocuments = ""
        # check if windows version is XP
        winversion = platform.version()
        if int(winversion[0]) < 6:
            mydocuments = os.path.join("C:\\Documents and Settings",
                                       username,
                                       "My Documents") + "\\"

            _log("get_skins_path", "Found Windows XP or lower." +
                 " Skins path assumed to be " + mydocuments +
                 "Rainmeter\\Skins\\")
        else:
            mydocuments = os.path.join("C:\\Users",
                                       username,
                                       "Documents") + "\\"

            _log("get_skins_path", "Found Windows Vista or higher." +
                 " Skins path assumed to be " + mydocuments +
                 "Rainmeter\\Skins\\")

        _log("get_skins_path", "Skin path guessed from user name" +
             " and Windows version")
        return os.path.join(mydocuments, "Rainmeter\\Skins") + "\\"


def get_plugins_path():
    """Get the value of the #PLUGINSPATH# variable"""

    settingspath = settings_path()
    if not settingspath:
        return
    return os.path.join(settingspath, "Plugins") + "\\"


def get_addons_path():
    """Get the value of the #ADDONSPATH# variable"""

    settingspath = settings_path()
    if not settingspath:
        return
    return os.path.join(settingspath, "Addons") + "\\"


def get_current_path(filepath):
    """Get the value of the #CURRENTPATH# variable for the specified path.

    Returns None if the file path is not in the skins folder

    """

    filepath = os.path.normpath(filepath)

    skinspath = skins_path()
    if not skinspath or not filepath.startswith(skinspath):
        _log("get_current_path", "current path could not be found because" +
             " either the skins path could not be found or the current file" +
             " is not located in the skins path.")
        return

    if os.path.isfile(filepath):
        return os.path.dirname(filepath) + "\\"
    else:
        return filepath + "\\"


def get_root_config_path(filepath):
    """Get the value of the #ROOTCONFIGPATH# variable for the specified path

    Returns None if the path is not in the skins folder

    """

    filepath = os.path.normpath(filepath)

    skinspath = skins_path()
    if not skinspath or not filepath.startswith(skinspath):
        _log("get_root_config_path", "root config path could not be found" +
             " because either the skins path could not be found or the" +
             " current file is not located in the skins path.")
        return

    relpath = os.path.relpath(filepath, skinspath)
    _log("get_root_config_path",
         os.path.join(skinspath, relpath.split("\\")[0]) + "\\")

    return os.path.join(skinspath, relpath.split("\\")[0]) + "\\"


def get_current_file(filepath):
    """Get the value of the #CURRENTFILE# variable for the specified path

    Returns None if the path is not in the skins folder

    """

    filepath = os.path.normpath(filepath)

    skinspath = skins_path()
    if not skinspath or not filepath.startswith(skinspath):
        _log("get_current_file", "current file could not be found because" +
             " either the skins path could not be found or the current" +
             " file is not located in the skins path.")
        return

    if os.path.isfile(filepath):
        return os.path.basename(filepath)
    else:
        _log("get_current_file", "specified path is not a file.")
        return


def get_current_config(filepath):
    """Get the value of the #CURRENTCONFIG# variable for the specified path

    Returns None if the path is not in the skins folder

    """

    filepath = os.path.normpath(filepath)

    skinspath = skins_path()
    if not skinspath or not filepath.startswith(skinspath):
        _log("get_current_config", "current config could not be found" +
             " because \either the skins path could not be found or the" +
             " current file is not located in the skins path.")
        return

    if os.path.isfile(filepath):
        filepath = os.path.dirname(filepath)

    return os.path.relpath(filepath, skinspath)


def get_resources_path(filepath):
    """Get the value of the #@# variable for the specified path

    Returns None if the path is not in the skins folder

    """

    rfp = get_root_config_path(filepath)

    if not rfp:
        return
    _log("get_resources_path", os.path.join(rfp, "@Resources") + "\\")
    return os.path.join(rfp, "@Resources") + "\\"


def replace_variables(string, filepath):
    """Replace Rainmeter built-in variables and Windows environment variables
    in string.

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

    # lambdas for lazy evaluation
    variables = {"#CURRENTFILE#": lambda: get_current_file(filepath),
                 "#CURRENTPATH#": lambda: get_current_path(filepath),
                 "#ROOTCONFIGPATH#": lambda: get_root_config_path(filepath),
                 "#CURRENTCONFIG#": lambda: get_current_config(filepath),
                 "#@#": lambda: get_resources_path(filepath),
                 "#SKINSPATH#": lambda: skins_path(),
                 "#SETTINGSPATH#": lambda: settings_path(),
                 "#PROGRAMPATH#": lambda: program_path(),
                 "#PROGRAMDRIVE#": lambda: program_drive(),
                 "#ADDONSPATH#": lambda: addons_path(),
                 "#PLUGINSPATH#": lambda: plugins_path()}

    pattern = re.compile("(?i)" + "|".join(list(variables.keys())))
    # replace Rainmeter variables
    repl = pattern.sub(lambda x: variables[x.group().upper()](),
                       string)
    # expand windows environment variables
    repl = os.path.expandvars(repl)
    return repl


def make_path(string, filepath):
    """Make the string into an absolute path of an existing file or folder,

    replacing Rainmeter built-in variables relative to the file specified in
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
        abso = norm
        if curpath:
            abso = os.path.join(curpath, norm)
        else:
            abso = os.path.join(os.path.dirname(filepath), norm)

        if os.path.exists(abso):
            return abso

        # if that doesn't work, try relative to skins path
        # (for #CURRENTCONFIG#)
        abso = os.path.join(skins_path(), norm)
        if os.path.exists(abso):
            return abso
    # for absolute paths, try opening containing folder if file does not exist
    else:
        if os.path.exists(norm):
            return norm

        if os.path.exists(os.path.dirname(norm)):
            return os.path.dirname(norm)

    return


# Initialize Module
# Global Variables
settings = None
log = None

_program_path = None
_program_drive = None
_settings_path = None
_skins_path = None
_plugins_path = None
_addons_path = None


# Called automatically from ST3 if plugin is loaded
# Is required now due to async call and ignoring sublime.* from main routine
def plugin_loaded():
    # define variables from the global scope
    global settings
    global log

    global _program_path
    global _program_drive
    global _settings_path
    global _skins_path
    global _plugins_path
    global _addons_path

    settings = sublime.load_settings("Rainmeter.sublime-settings")
    log = settings.get("rainmeter_enable_logging", False)


    # Cache the paths
    _program_path = get_program_path()
    _program_drive = get_program_drive()
    _settings_path = get_settings_path()
    _skins_path = get_skins_path()
    _plugins_path = get_plugins_path()
    _addons_path = get_addons_path()

    if log:
        print("#PROGRAMPATH#:\t" + program_path() +
              "\n#PROGRAMDRIVE#:\t" + program_drive() +
              "\n#SETTINGSPATH#:\t" + settings_path() +
              "\n#SKINSPATH#:\t" + skins_path() +
              "\n#PLUGINSPATH#:\t" + plugins_path() +
              "\n#ADDONSPATH#:\t" + addons_path())

class MeterAutoComplete(sublime_plugin.EventListener):

    # only show our completion list because nothing else makes sense in this context
    flags = sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS
    scope = "source.rainmeter"

    comment_exp = re.compile(r'^\s*;.*')
    meter_exp = re.compile(r'^\s*')

    completions = [
        # measures
        (re.compile(r'^\s*Measure\s*=\s*'), [
            # key, value
            ["Calc", "Calc"], 
            ["CPU", "CPU"],
            ["FreeDiskSpace", "FreeDiskSpace"],
            ["Loop", "Loop"],

            # memory measure
            ["Memory", "Memory"],
            ["PhysicalMemory ", "PhysicalMemory "],
            ["SwapMemory", "SwapMemory"],

            # net measure
            ["NetIn", "NetIn"],
            ["NetOut", "NetOut"],
            ["NetTotal", "NetTotal"],

            ["Plugin", "Plugin"],
            ["Registry", "Registry"],
            ["Script", "Script"],
            ["String", "String"],
            ["Time", "Time"],
            ["Uptime", "Uptime"]
        ]),

        # meters
        (re.compile(r'^\s*Meter\s*=\s*'), [
            # key, value
            ["Bar", "Bar"],
            ["Bitmap", "Bitmap"],
            ["Button", "Button"],
            ["Histogram", "Histogram"],
            ["Image", "Image"],
            ["Line", "Line"],
            ["Rotator", "Rotator"],
            ["Roundline", "Roundline"],
            ["Shape", "Shape"],
            ["String", "String"]
        ]),
        # general options

        # bar
        # bar orientation
        (re.compile(r'^\s*BarOrientation\s*=\s*'), [
            # key, value
            ["Horizontal", "Horizontal"],
            ["Vertical\tDefault", "Vertical"]
        ]),

        # bar flip
        (re.compile(r'^\s*Flip\s*=\s*'), [
            # key, value
            ["0\tDefault", "0"],
            ["1\tBar is flipped", "1"]
        ]),

        # bitmap

        # button
        # histogram
        # image
        # line
        # rotator
        # roundline
        # shape
        # string

        # plugins
        (re.compile(r'^\s*Plugin\s*=\s*'), [
            # key, value
            ["ActionTimer", "ActionTimer"],
            ["AdvancedCPU", "AdvancedCPU"],
            ["AudioLevel", "AudioLevel"],
            ["CoreTemp", "CoreTemp"],
            ["FileView", "FileView"],
            ["FolderInfo", "FolderInfo"],
            ["InputText", "InputText"],
            ["iTunes", "iTunesPlugin"],
            ["MediaKey", "MediaKey"],
            ["NowPlaying", "NowPlaying"],
            ["PerfMon", "PerfMon"],
            ["Ping", "PingPlugin"],
            ["Power", "PowerPlugin"],
            ["Process", "Process"],
            ["Quote", "QuotePlugin"],
            ["RecycleManager", "RecycleManager"],
            ["ResMon", "ResMon"],
            ["RunCommand", "RunCommand"],
            ["SpeedFan", "SpeedFanPlugin"],
            ["SysInfo", "SysInfo"],
            ["WebParser", "WebParser"],
            ["WiFiStatus", "WiFiStatus"],
            ["Win7Audio", "Win7AudioPlugin"],
            ["WindowMessage", "WindowMessagePlugin"]
        ]),

        

    ]

    def on_query_completions(self, view, prefix, locations):

        for location in locations:
            # checks if the current scope is correct so it is only called in the files with the correct scope
            # here is scope only rainmeter files
            if view.match_selector(location, self.scope):
                # find last occurance of the [] to determine the ini sections
                size = view.size()
                startContent = view.substr(sublime.Region(0, location))
                endContent = view.substr(sublime.Region(location, size))
                line = view.line(location)
                lineContents = view.substr(line)

                start_index = self.get_current_section_content_start_index(startContent)
                end_index = self.get_current_section_content_end_index(endContent, location, size)

                section = view.substr(sublime.Region(start_index, end_index))
                lines = section.splitlines()
                # filter empty lines
                lines = list(filter(None, lines))
                # filter comments
                lines = list(filter(lambda line: not self.comment_exp.search(line),lines))


                # for line in lines:
                #     print(line)
                #     for exp, elements in self.completions:
                #         if exp.search(line):
                            # print(line)

                
                # starts with Measure, followed by an equal sign
                for exp, elements in self.completions:
                    if exp.search(lineContents):
                        return (elements, self.flags)

        return None

    def get_current_section_content_start_index(self, startContent):
        matches = list(re.finditer('\[.*\]', startContent))
        if len(matches) > 0:
            lastMatch = matches[-1]
            return lastMatch.start()

        # no previous section found, hardly legal but who cares
        else: 
            return 0

    def get_current_section_content_end_index(self, endContent, offset, endIndex):
        matches = list(re.finditer('\[.*\]', endContent))
        if len(matches) > 0:
            firstMatch = matches[0]
            return firstMatch.start() + offset

        # no next section found
        else: 
            return endIndex


class SectionAutoComplete:
    bracket_expression = re.compile(r'^\s*\[.*\]\s*$')

    def get_current_section_content_start_index(self, startContent):
        matches = list(self.bracket_expression.finditer(startContent))
        if len(matches) > 0:
            lastMatch = matches[-1]
            return lastMatch.start()

        # no previous section found, hardly legal but who cares
        else: 
            return 0

    def get_current_section_content_end_index(self, endContent, offset, endIndex):
        matches = list(self.bracket_expression.finditer(endContent))
        if len(matches) > 0:
            firstMatch = matches[0]
            return firstMatch.start() + offset

        # no next section found
        else: 
            return endIndex

class SkinRainmeterSectionKeyAutoComplete(sublime_plugin.EventListener, SectionAutoComplete):
    
    @staticmethod
    def get_completions():
        dir_path = os.path.dirname(os.path.realpath(__file__))

        with open(dir_path + "/completion/skin_rainmeter_section.yaml", 'r') as skin_rainmeter_section_stream, open(dir_path + "/completion/meters_general_image_options.yaml", 'r') as meters_general_image_options_stream:
            try:
                skin_rainmeter_section = yaml.load(skin_rainmeter_section_stream)
                meters_general_image_options = yaml.load(meters_general_image_options_stream)

                skin_rainmeter_section['options'].extend(meters_general_image_options)

                return skin_rainmeter_section

                # print(skin_rainmeter_section)
            except yaml.YAMLError as e:
                print(e)

    @staticmethod
    def get_compiled_completions(options):
        keys = []
        for option in options:
            title = option['title'] + "\t" + option['hint']
            result = None
            if 'value' in option: 
                result = option['value'] 
            else: 
                result = option['title']

            pair = (title, result)
            keys.append(pair)

        return keys

    # only show our completion list because nothing else makes sense in this context
    flags = sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS
    scope = "source.rainmeter"
    
    all_completions = get_completions.__func__()

    comment_exp = re.compile(r'^\s*;.*')
    rm_exp = re.compile(r'^\s*\[Rainmeter\]\s*$', re.I)
    all_completions = get_compiled_completions.__func__(all_completions['options'])
    after_equal_exp = re.compile(r'^.*\=\s*')

    def on_query_completions(self, view, prefix, locations):
        for location in locations:
            # checks if the current scope is correct so it is only called in the files with the correct scope
            # here is scope only rainmeter files
            if not view.match_selector(location, self.scope):
                _log("on_query_completions", "not in rainmeter scope")
                return None

            # ignore on comment lines
            line = view.line(location)
            lineContents = view.substr(line)
            if self.comment_exp.search(lineContents):
                _log("on_query_completions", "found comment")
                return None

            # only do key completion if we are in the key are
            # that means in front of the equal or no equal at all
            if self.after_equal_exp.search(lineContents):
                _log("on_query_completions", "after equal sign")
                return None

            # find last occurance of the [] to determine the ini sections
            size = view.size()
            startContent = view.substr(sublime.Region(0, location))
            endContent = view.substr(sublime.Region(location, size))

            start_index = self.get_current_section_content_start_index(startContent)
            end_index = self.get_current_section_content_end_index(endContent, location, size)

            section = view.substr(sublime.Region(start_index, end_index))
            lines = section.splitlines()
            # filter empty lines
            lines = list(filter(None, lines))
            # filter comments
            lines = list(filter(lambda line: not self.comment_exp.search(line),lines))

            if not lines:
                _log("on_query_completions", "section is empty")
                return None
        
            first_line = lines[0]

            # currently in the [rainmeter] section
            if not self.rm_exp.search(first_line):
                _log("on_query_completions", "not in rainmeter section")
                return None

            # filter by already existing keys
            completions = []

            for completion in self.all_completions:
                key, value = completion

                contained = 0
                for line in lines:
                    regex = r"\s*(" + re.escape(value) + r")\s*\=?.*$"
                    if re.match(regex, line, re.I):
                        contained = 1
                        break

                if contained == 0:
                    completions.append(completion)
                
            return (completions, self.flags)

        return None
