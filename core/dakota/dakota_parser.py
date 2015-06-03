# Standard Python modules
# =======================
import json
from collections import OrderedDict

from PyQt5.QtCore import qDebug

# DICE modules
# ============
from core.tools.path_helper import PathHelper
from core.third_party.ply_parser import PlyParser
from core.third_party.ply.lex import TOKEN
from core.dakota.dakota_input_file_generator import DakotaInputFileGenerator


class ParsedDakotaInputFile:
    """
    Input-File whose complete representation is read into
    memory, can be manipulated and afterwards written to disk.
    """

    def __init__(self, name):
        """
        :param name: The name of the input file
        :return:
        """

        self.name = name
        self.content = None

        self.read_file(name)
        self.parse()

        self.writeFile()

    def read_file(self, name):
        """ read file into memory """
        with open(name, 'r') as file:
            self.content = file.read()

    def parse(self):
        """
        Creates the representation of the file
        :param content:
        :return:
        """
        try:
            parser = DakotaInputFileParser(self.content)
        except:
            raise Exception

        self.content = parser.get_data()
        return self.content

    def writeFile(self, content=None):
        """
        writes the file from memory
        """
        if self.name is not None:
            if content is not None:
                self.content = content
            if self.content is not None:
                txt = str(self)
                with open(self.name, 'w') as f:
                    f.write(txt)

    def __str__(self):
        """
        converts dict data to string for pretty print
        """
        string = '# File generated by DICE \n'
        string += '# Have fun!\n'
        string += '# ====================== \n\n'

        generator = DakotaInputFileGenerator(self.content)
        string += generator.make_string()

        string += "\n\n"

        return string

    def __contains__(self,key):
        return key in self.content

    def __getitem__(self, key):
        for i, k in enumerate(self.content):
            for keyword in k:
                if keyword == key:
                    return self.content[i][key]

    def __setitem__(self, key, value):
        for i, k in enumerate(self.content):
            for keyword in k:
                if keyword == key:
                    self.content[i][key] = value

    def __delitem__(self,key):
        for i, k in enumerate(self.content):
            for keyword in k:
                if keyword == key:
                    del self.content[key]

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        for key in self.content:
            yield key


class DakotaInputFileParser:
    """
    Parses a string that contains the contents of a Dakota-Input-File
    """

    def __init__(self, content):

        self.data = None
        self.data = self.parse(content)

    def get_data(self):
        """
        Get the data structure
        """
        return self.data

    def parse(self, content):
        """
        Do the actual parsing
        """

        # Create a list of all entries in the input file
        # ==============================================
        dp = DakotaParser()
        blocks_list = dp.parse(content)

        # Sort the list according to the dakota specs in dakota.json
        # ==========================================================
        sb = SortedBlock(blocks_list)
        parsed_content = sb.get()

        return parsed_content


class DakotaSpecs(PathHelper):

    def __init__(self):

        with open(self.module_path("dakota.json"), "r") as file:
            self.dakota_specs = json.load(file)["input"]["keyword"]

    def get_specs(self):
        return self.dakota_specs


class DakotaParser(PlyParser):

    def __init__(self, debug=False):

        self.debug = debug

        PlyParser.__init__(self, debug=debug)

    tokens = (
        'KEYWORD',
        'ICONST',
        'FCONST',
        'DQSCONST',
        'SCONST',
        'COMMENT',
        'EQUALS',
        'COMMA'
    )

    keyword_identifier = r'[a-zA-Z_][+\-<>().\*|a-zA-Z_0-9&%:]*'

    @TOKEN(keyword_identifier)
    def t_KEYWORD(self, t):
        return t

    t_EQUALS  = r'='

    t_ICONST = r'(-|)\d+([uU]|[lL]|[uU][lL]|[lL][uU])?'

    # http://stackoverflow.com/questions/13252101/regular-expressions-match-floating-point-number-but-not-integer
    t_FCONST = r'[+-]?(?=\d*[.eE])(?=\.?\d)\d*\.?\d*(?:[eE][+-]?\d+)?'

    t_SCONST = r'\"([^\\\n]|(\\.))*?\"'

    t_DQSCONST = r'\'([^\\\n]|(\\.))*?\''

    t_ignore=" \t\r"

    def t_COMMENT(self, t):
        r'\#.*'
        pass

    def t_COMMA(self, t):
        r','
        pass

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        # print("Illegal character '%s'" % t.value[0])
        # t.lexer.skip(1)
        msg="Illegal character '%s' in line %d (pos: %d)" % (
            t.value[0],
            t.lexer.lineno,
            t.lexer.lexpos)
        print(msg)

    # Parsing rules
    # =============

    def p_block(self, p):
        '''block : block key_value
                    | key_value'''
        if len(p) == 2:
            p[0] = [p[1]]

        else:
            p[0] = p[1]
            p[0].append(p[2])
        # print('BLOCK', p[0])

    def p_key_value(self, p):
        '''key_value : KEYWORD EQUALS string_value
                    | KEYWORD EQUALS integer
                    | KEYWORD EQUALS float
                    | KEYWORD EQUALS reallist
                    | KEYWORD reallist
                    | KEYWORD EQUALS stringlist
                    | KEYWORD stringlist
                    | KEYWORD'''
        if len(p) == 2:
            p[0] = {p[1]: ''}
        elif len(p) == 3:
            p[0] = { p[1]: p[2] }
        else:
            p[0] = {p[1]: p[3]}
        # print("KEY_VALUE", p[0])
        # self.sorted_blocks.add_item(p[1], p[0])

    def p_reallist(self, p):
        '''reallist : reallist number
                    | number '''
        if len(p) == 2:
            p[0] = [ p[1] ]
        else:
            p[0] = p[1]
            p[0].append(p[2])

    def p_stringlist(self, p):
        '''stringlist : stringlist  string_value
                      | string_value'''
        if len(p) == 2:
            p[0] = [ p[1] ]
        else:
            p[0] = p[1]
            p[0].append(p[2])

    def p_number(self, p):
        '''number : integer
                  | float'''
        p[0] = p[1]

    def p_string_value(self, p):
        '''string_value :  SCONST
                        |  DQSCONST '''
        if '"' in p[1]:
            p[0] = p[1].split('"')[1]
        elif "'" in p[1]:
            p[0] = p[1].split("'")[1]
        # print("VALUE", p[0])

    def p_integer(self,p):
        '''integer : ICONST'''
        p[0] = int(p[1])

    def p_float(self,p):
        '''float : FCONST'''

        p[0] = float(p[1])

    def p_empty(self, p):
        'empty :'
        pass

    def p_error(self, p):
        print("Syntax error at '%s'" % p.value)


class SortedBlock(DakotaSpecs, PathHelper):

    def __init__(self, parsed_dicts_list):

        DakotaSpecs.__init__(self)

        # list of dicts from the ply parser
        # =================================
        self.parsed_dicts_list = parsed_dicts_list
        self.blocks_key_list = []

        # specs dict from the dakota.json (converted from dakota.xml)
        # ===========================================================
        ds = DakotaSpecs()
        self.dakota_specs = ds.get_specs()

        # sorted result for DICE
        # ======================
        self.sorted_blocks = []
        self.unknown_keywords_list = []
        self.sort_dicts()

    def get(self):
        return self.sorted_blocks

    def sort_dicts(self):
        '''
        Creates a tree according to dakota specs from parsed dict_list
        :return:
        '''

        # run one time to setup top structure list
        # ========================================
        for block_dict in self.parsed_dicts_list:
            for key in block_dict:
                self.blocks_key_list.append(key)
                if self.is_top_node(key):
                    block_dict[key] = OrderedDict()
                    self.sorted_blocks.append(block_dict)

        # create key-path dict for the rest
        # =================================
        # print(self.find_key_path(self.dakota_specs, 'sampling')[0])
        for block_dict in self.parsed_dicts_list:
            for key in block_dict:
                key_path = self.find_key_path(self.dakota_specs, key)[0]
                value = block_dict[key]
                if len(key_path) != 0:
                    self.__create_dict(self.sorted_blocks, key_path, key, value)
                else:
                    self.unknown_keyword(key, value)
                    qDebug("Unknown keyword "+key)

    def __create_dict(self, block_dict, key_path, key, value):
        head, *tails = key_path
        for i, k in enumerate(self.sorted_blocks):
            for keyword in k:
                if keyword == head and tails:
                    block_dict[i][head][key] = value

    def is_top_node(self, keyword):
        for keyword_dict in self.dakota_specs:
            if keyword_dict["@name"] == keyword:
                return True

    def find_key_path(self, node, value, path=[], found=False):

        if isinstance(node, list):
            for list_item in node:
                tmp_path, found = self.find_key_path(list_item, value)

                if found:
                    return tmp_path, True

        elif isinstance(node, dict):
            if '@id' in node:
                if node["@name"] == value:
                    return [value], True

            if 'alias' in node:
                if '@name' in node['alias']:
                    if node['alias']['@name'] == value:
                        return [value], True

            for elem in node:
                tmp_path, found = self.find_key_path(node[elem], value)

                if found and '@name' in node and self.__is_in_parsed_block_list(node['@id']):
                    path = [node['@name']] + tmp_path
                    return path, found
                elif found:
                    path = tmp_path
                    return path, found
        return path, False

    def __is_in_parsed_block_list(self, keyword):
        for block_dict in self.parsed_dicts_list:
            for key in block_dict:
                if key == keyword:
                    return True
        return False

    def unknown_keyword(self, keyword, value):
        self.unknown_keywords_list.append({keyword: value})
