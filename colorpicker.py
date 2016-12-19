"""This module is about the integration with the color picker.

The color picker can detect a color in a substring
and launch a tool to display the current color,
change it and thus also replace the old color.

It supports both ways Rainmeter defines color.

* RRGGBB
* RRGGBBAA
* RRR,GGG,BBB
* RRR,GGG,BBB,AAA

which is hexadecimal and decimal format.
"""
import os
import re
import subprocess

import sublime
import sublime_plugin

from . import logger
from .color import converter

# if sublime.platform() == 'windows':
#     import ctypes
#     from ctypes import c_int32, c_uint32, c_void_p, c_wchar_p, POINTER

#     class CHOOSECOLOR(ctypes.Structure): # pylint: disable=R0903; this extends a data class
#         """Data mapping representation contained for the color chooser."""

#         _fields_ = [('lStructSize', c_uint32),
#                     ('hwndOwner', c_void_p),
#                     ('hInstance', c_void_p),
#                     ('rgbResult', c_uint32),
#                     ('lpCustColors', POINTER(c_uint32)),
#                     ('Flags', c_uint32),
#                     ('lCustData', c_void_p),
#                     ('lpfnHook', c_void_p),
#                     ('lpTemplateName', c_wchar_p)]

#     CustomColorArray = c_uint32 * 16
#     CC_SOLIDCOLOR = 0x80
#     CC_RGBINIT = 0x01
#     CC_FULLOPEN = 0x02

#     ChooseColorW = ctypes.windll.Comdlg32.ChooseColorW
#     ChooseColorW.argtypes = [POINTER(CHOOSECOLOR)]
#     ChooseColorW.restype = c_int32

#     GetDC = ctypes.windll.User32.GetDC
#     GetDC.argtypes = [c_void_p]
#     GetDC.restype = c_void_p

#     ReleaseDC = ctypes.windll.User32.ReleaseDC
#     ReleaseDC.argtypes = [c_void_p, c_void_p]  # hwnd, hdc
#     ReleaseDC.restype = c_int32




class RainmeterColorPickCommand(sublime_plugin.TextCommand): # pylint: disable=R0903; we only need one method
    """Sublime Text integration running this through an action."""

    output = None

    def run(self, _):
        """
        Method is provided by Sublime Text through the super class TextCommand.

        This is run automatically if you initialize the command
        through an "command": "rainmeter_color_pick" command.
        """
        sublime.set_timeout_async(self.delegate_async, 0)

    def delegate_async(self):
        """Proxy for calling multiple methods."""
        self.__run_picker()
        self.__write_back()

    def __get_first_selection(self):
        selections = self.view.sel()
        first_selection = selections[0]

        return first_selection

    def __get_selected_line_index(self):
        first_selection = self.__get_first_selection()
        selection_start = first_selection.begin()
        line_cursor = self.view.line(selection_start)
        line_index = line_cursor.begin()

        return line_index

    def __get_selected_line_content(self):
        first_selection = self.__get_first_selection()
        selection_start = first_selection.begin()
        line_cursor = self.view.line(selection_start)
        line_content = self.view.substr(line_cursor)

        return line_content

    def __get_selected_color_or_none(self):
        """Return None in case of not finding the color aka no color is selected."""
        caret = self.__get_first_selection().begin()
        line_index = self.__get_selected_line_index()
        line_content = self.__get_selected_line_content()

        dec_color_exp = re.compile(
            r"(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(\d{1,3}))?"
        )

        # catch case with multiple colors in same line
        for match in dec_color_exp.finditer(line_content):
            # need to shift the caret to the current line
            if line_index + match.start() <= caret <= line_index + match.end():
                rgba_raw = match.groups()
                rgba = [int(color) for color in rgba_raw if color is not None]
                hexes = converter.rgbs_to_hexes(rgba)
                hex_string = converter.hexes_to_string(hexes)
                with_alpha = self.__convert_hex_to_hex_with_alpha(hex_string)

                return with_alpha

        # if no match was iterated we process furthere starting here
        hex_color_exp = re.compile(r"(?:[0-9a-fA-F]{2}){3,4}")
        
        # we can find multiple color values in the same row
        # after iterating through the single elements
        # we can use start() and end() of each match to determine the length
        # and thus the area the caret had to be in,
        # to identify th1e one we are currently in
        for match in hex_color_exp.finditer(line_content):
            low = line_index + match.start()
            high = line_index + match.end()

            if low <= caret <= high:
                hex_values = match.group(0)
                # color picker requires RGBA
                with_alpha = self.__convert_hex_to_hex_with_alpha(hex_values)

                return with_alpha
            else:
                logger.info(__file__, "__get_selected_color_or_none(self)", low)
                logger.info(__file__, "__get_selected_color_or_none(self)", high)
                logger.info(__file__, "__get_selected_color_or_none(self)", caret)

        return

    def __convert_hex_to_hex_with_alpha(self, hexes):
        """If no alpha value is provided it defaults to FF."""
        if len(hexes) == 6:
            return hexes + "FF"
        else:
            return hexes

    def __run_picker(self):
        maybe_color = self.__get_selected_color_or_none()
        
        # no color selected, we call the color picker and insert the color at that position
        color = "FFFFFFFF" if maybe_color is None else maybe_color

        project_root = os.path.dirname(__file__)
        picker_path = os.path.join(project_root, "color", "picker", "ColorPicker_win.exe")
        picker = subprocess.Popen(
            [picker_path, color],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        out, err = picker.communicate()
        self.output = out.decode("utf-8")
        logger.info(__file__, "__run_picker(self)", "output: " + self.output)
        error = err.decode("utf-8")
        if error is not None and len(error) != 0:
            logger.error(__file__, "__run_picker(self)", "Color Picker Error:\n" + err)

    def __write_back(self):
        if self.output is not None and len(self.output) == 9 and self.output != 'CANCEL':
            logger.info(__file__, "__write_back(self)", "can write back: " + self.output)
            # self.view.substr(self.words[0][0])
            # self.view.run_command(
                # "ch_replace_color",
                # {
                    # "words": "\t".join(map(lambda x: str((x[0], x[1], self.output)), self.words))
                # }
            # )

        # reset output value so next iteration does not go through the if close
        self.output = None


    #     sel = self.view.sel()
    #     start_color_win = 0x000000

    #     # Get the currently selected color - if any
    #     if len(sel) > 0:
    #         selected = self.view.substr(self.view.word(sel[0])).strip()
    #         if selected.startswith('#'):
    #             selected = selected[1:]
    #         if self.__is_valid_hex_color(selected):
    #             if len(selected) > 6:
    #                 selected = selected[0:6]
    #             start_color_win = self.__hexstr_to_bgr(selected)

    #     if sublime.platform() == 'windows':

    #         settings = sublime.load_settings("ColorPicker.sublime-settings")
    #         custom_colors = settings.get("custom_colors", ['0'] * 16)

    #         if len(custom_colors) < 16:
    #             custom_colors = ['0'] * 16
    #             settings.set('custom_colors', custom_colors)

    #         choose_color = CHOOSECOLOR()
    #         ctypes.memset(ctypes.byref(choose_color), 0, ctypes.sizeof(choose_color))
    #         choose_color.lStructSize = ctypes.sizeof(choose_color)
    #         choose_color.hwndOwner = None
    #         choose_color.Flags = CC_SOLIDCOLOR | CC_FULLOPEN | CC_RGBINIT
    #         choose_color.rgbResult = c_uint32(start_color_win)
    #         choose_color.lpCustColors = self.__to_custom_color_array(custom_colors)

    #         if ChooseColorW(ctypes.byref(choose_color)):
    #             color = self.__bgr_to_hexstr(choose_color.rgbResult)
    #         else:
    #             color = None

    #     if color:
    #         # Replace all regions with color
    #         for region in sel:
    #             word = self.view.word(region)
    #             # If the selected word is a valid color, replace it
    #             if self.__is_valid_hex_color(self.view.substr(word)):
    #                 if len(self.view.substr(word)) > 6:
    #                     word = sublime.Region(word.a, word.a + 6)
    #                 # Include '#' if present
    #                 self.view.replace(edit, word, color)
    #             # If the selected region starts with a #, keep it
    #             elif self.view.substr(region).startswith('#'):
    #                 reduced = sublime.Region(region.begin() + 1, region.end())
    #                 if self.__is_valid_hex_color(self.view.substr(reduced)):
    #                     if len(reduced) > 6:
    #                         reduced = sublime.Region(reduced.a, reduced.a + 6)
    #                     self.view.replace(edit, reduced, color)
    #                 else:
    #                     self.view.replace(edit, region, '#' + color)
    #             # Otherwise just replace the selected region
    #             else:
    #                 self.view.replace(edit, region, color)

    # @classmethod
    # def __to_custom_color_array(cls, custom_colors):
    #     cca = CustomColorArray()
    #     for i in range(16):
    #         cca[i] = int(custom_colors[i])
    #     return cca

    # @classmethod
    # def __from_custom_color_array(cls, custom_colors):
    #     cca = [0] * 16
    #     for i in range(16):
    #         cca[i] = str(custom_colors[i])
    #     return cca

    # @classmethod
    # def __is_valid_hex_color(cls, string):
    #     if len(string) not in (3, 6, 8):
    #         return False
    #     try:
    #         return 0 <= int(string, 16) <= 0xffffffff
    #     except ValueError:
    #         return False

    # byte_table = list(['{0:02X}'.format(b) for b in range(256)])

    # @classmethod
    # def __bgr_to_hexstr(cls, bgr):
    #     # 0x00BBGGRR
    #     blue = cls.byte_table[(bgr >> 16) & 0xff]
    #     green = cls.byte_table[(bgr >> 8) & 0xff]
    #     red = cls.byte_table[bgr & 0xff]

    #     return red + green + blue

    # @classmethod
    # def __hexstr_to_bgr(cls, hexstr):
    #     if len(hexstr) == 3:
    #         hexstr = hexstr[0] + hexstr[0] + hexstr[1] + \
    #             hexstr[1] + hexstr[2] + hexstr[2]

    #     red = int(hexstr[0:2], 16)
    #     green = int(hexstr[2:4], 16)
    #     blue = int(hexstr[4:6], 16)

    #     return (blue << 16) | (green << 8) | red
