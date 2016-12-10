import yaml

import sublime

# import own libs
from ... import logger
from ...completion.levenshtein import levenshtein
from ...completion.yaml_content_reader import YamlContentReader


class SkinMetadataSectionAutoComplete(YamlContentReader):

    def __get_completions(self):
        try:
            skin_metadata_section_content = self._get_yaml_content("completion/skin/", "metadata_section.yaml")
            skin_metadata_section = yaml.load(skin_metadata_section_content)

            return skin_metadata_section

        except yaml.YAMLError as error:
            logger.error(__file__, "get_completions", error)
            return []

    def __get_compiled_key_completions(self, options):
        keys = []
        for option in options:
            title = option['title'] + "\t" + option['hint']

            if 'value' in option:
                result = option['value']
            else:
                result = option['title']

            pair = (title, result)
            keys.append(pair)

        return keys

    def __lazy_initialize_completions(self):
        # use lazy initialization because else the API is not available yet
        if not self.all_completions:
            self.all_completions = self.__get_completions()
            self.all_key_completions = self.__get_compiled_key_completions(self.all_completions)

    def __filter_completions_by_key_already_used(self, keyvalues):
        """
        In Rainmeter a key can only be used once in a section statement.
        If you declare it twice this is a code smell.
        """
        # filter by already existing keys
        completions = []

        for completion in self.all_key_completions:
            # trigger is not used here
            _, content = completion

            contained = 0
            # value not used here
            for key, _ in keyvalues:
                if key.casefold() == content.casefold():
                    contained = 1
                    break

            if contained == 0:
                completions.append(completion)

    # only show our completion list because nothing else makes sense in this context
    flags = sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS

    all_completions = None
    all_key_completions = None

    def get_key_context_completion(self, view, prefix, location, line_content, section, keyvalues):
        if section.casefold() != "Metadata".casefold():
            return None

        self.__lazy_initialize_completions()
        completions = self.__filter_completions_by_key_already_used(keyvalues)

        # no results, means all keys are used up
        if not completions:
            return None

        # only show sorted by distance if something was already typed because distance to empty string makes no sense
        if line_content != "":
            # sort by levenshtein distance
            sorted_completions = sorted(completions, key=lambda completion: levenshtein(completion[1], prefix))
            return sorted_completions, self.flags
        else:
            return completions, self.flags

    def get_value_context_completion(self, view, prefix, location, line_content, section, key_match, keyvalues):
        return None
