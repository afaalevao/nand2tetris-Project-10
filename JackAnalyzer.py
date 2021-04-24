'''
Andrew Faalevaao
Enrique Gonzalez
CSCI 410 Elements of Computing Systems
Project 10: Jack Compiler 1
'''

import sys
import os
import re


class Tokenizer:

    def __init__(self, jack_filename):
        self.keywords = {'class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int',
                         'char', 'boolean', 'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if',
                         'else', 'while', 'return'}
        self.symbols = {'{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/', '&', '|', '<', '>', '=', '~'}
        self.token_specification = [
            ('MLC_START', r'\/\*'),  # Multi-line comment start
            ('MLC_FINISH', r'\*\/'),  # Multi-line comment finish
            ('SLC_START', r'\/{2}'),  # Single line comment start
            ('IDENTIFIER', r'[a-zA-Z_][A-Za-z\d]*'),  # Identifiers
            ('INT_CONST', r'\d+'),  # Integer constants
            ('STRING_CONST', r'\".+\"'),  # String constants
            ('OTHER', r'[^\s]'),  # Other
        ]
        self.tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.token_specification)
        self.xml_translate = {'KEYWORD': 'keyword', 'SYMBOL': 'symbol', 'INT_CONST': 'integerConstant',
                              'STRING_CONST': 'stringConstant', 'IDENTIFIER': 'identifier'}

        self.jack = open(jack_filename, 'r')
        self.xmlT_filename = os.path.dirname(jack_filename) + '\\xml\\' + (os.path.split(jack_filename)[1]).split('.')[0] + 'T.xml'

        if not os.path.exists(os.path.dirname(self.xmlT_filename)):
            os.makedirs(os.path.dirname(self.xmlT_filename))

        self.xmlT = open(self.xmlT_filename, 'w')
        self.xmlT.write('<tokens>' + '\n')
        self.mlc_flag = False  # multi line comment (/* comment */)
        self.readEOF = False
        self.token_list = []
        self.token_list_temp = []
        self.token_list_k = 0
        self.rebuffer()

    def __del__(self):
        self.xmlT.write('</tokens>')
        self.xmlT.close()

    def get_token_type(self):
        return self.token_list[self.token_list_k][0]

    def get_token_value(self):
        return self.token_list[self.token_list_k][1]

    def advance(self):
        if not self.readEOF:
            self.token_list_k += 1
            if self.token_list_k >= len(self.token_list):
                self.rebuffer()

    def rebuffer(self):
        self.line = self.jack.readline()
        self.tokenize_line()
        while self.line != '' and len(self.token_list_temp) < 1:
            self.line = self.jack.readline()
            self.tokenize_line()
        if self.line == '':
            self.readEOF = True
            self.token_list_k -= 1
        else:
            self.token_list = self.token_list_temp[:]  # [:] creates a copy
            self.token_list_k = 0

    def tokenize_line(self):
        self.token_list_temp.clear()
        slc_flag = False  # single line comment (//comment)

        for mo in re.finditer(self.tok_regex, self.line):
            token_type = mo.lastgroup
            value = mo.group(token_type)

            if self.mlc_flag:
                if token_type == 'MLC_FINISH':
                    self.mlc_flag = False
            elif token_type == 'MLC_START':
                self.mlc_flag = True
            elif not slc_flag:
                if token_type == 'SLC_START':
                    slc_flag = True
                else:
                    if token_type == 'IDENTIFIER' and value in self.keywords:
                        token_type = 'KEYWORD'
                    elif token_type == 'STRING_CONST':
                        value = value[1:-1]
                    elif token_type == 'OTHER':
                        if value in self.symbols:
                            token_type = 'SYMBOL'
                        else:
                            token_type = 'MISMATCH'

                    self.write_token(token_type, value)
                    self.token_list_temp.append((token_type, value))

    def write_token(self, token_type, value):
        xml_value = str(value)

        if xml_value in ('<', '>', '&'):
            if xml_value == '<':
                xml_value = '&lt;'
            elif xml_value == '>':
                xml_value = '&gt;'
            else:
                xml_value = '&amp;'

        xml = '\t<' + self.xml_translate[token_type] + '> ' + xml_value + ' </' + self.xml_translate[token_type] + '>\n'
        self.xmlT.write(xml)


class Parser:

    def __init__(self, jack_token):
        self.token = jack_token
        self.xml_filename = self.token.xmlT_filename.split('T.')[0] + '.xml'

        if not os.path.exists(os.path.dirname(self.xml_filename)):
            os.makedirs(os.path.dirname(self.xml_filename))

        self.xml = open(self.xml_filename, 'w')
        self.tabk = 0

        if self.token.get_token_value() == 'class':
            self.compile_class()
        else:
            print('invalid syntax in init')

    def __del__(self):
        self.xml.close()

    def write_xml_non_terminal(self, s, tag_type):
        if tag_type == 'begin':
            self.xml.write('\t' * self.tabk + '<' + s + '>\n')
            self.tabk += 1
        elif tag_type == 'end':
            self.tabk -= 1
            self.xml.write('\t' * self.tabk + '</' + s + '>\n')
        else:
            self.xml.write('invalid type')

    def write_xml_terminal(self):
        xml_value = str(self.token.get_token_value())

        if xml_value in ('<', '>', '&'):
            if xml_value == '<':
                xml_value = '&lt;'
            elif xml_value == '>':
                xml_value = '&gt;'
            else:
                xml_value = '&amp;'

        self.xml.write('\t' * self.tabk + '<' + self.token.xml_translate[self.token.get_token_type()] + '> ' + xml_value + ' </' + self.token.xml_translate[self.token.get_token_type()] + '>\n')

    def expect_token_type(self, *token_type):
        if self.token.get_token_type() not in token_type:
            print('syntax error: expected tokenType in ' + str(token_type) + ' in routine ' + sys._getframe().f_back.f_code.co_name)
            print('source line: ', end='')

            for pair in self.token.token_list:
                print(pair[1] + ' ', end='')

            print('\ntoken index: ' + str(self.token.token_list_k))
            sys.exit(1)

    def expect_token_value(self, *token_value):
        if self.token.get_token_value() not in token_value:
            print('syntax error: expected tokenValue in ' + str(token_value) + ' in routine ' + sys._getframe().f_back.f_code.co_name)
            print('source line: ', end='')

            for pair in self.token.token_list:
                print(pair[1] + ' ', end='')

            print('\ntoken index: ' + str(self.token.token_list_k))
            sys.exit(1)

    def process_token_expecting_type(self, *token_type):
        self.expect_token_type(*token_type)
        self.write_xml_terminal()
        self.token.advance()

    def process_token_expecting_value(self, *token_value):
        self.expect_token_value(*token_value)
        self.write_xml_terminal()
        self.token.advance()

    def compile_class(self):
        self.write_xml_non_terminal('class', 'begin')
        self.process_token_expecting_value('class')
        self.process_token_expecting_type('IDENTIFIER')
        self.process_token_expecting_value('{')

        while self.token.get_token_value() != '}':
            if self.token.get_token_value() in ('static', 'field'):
                self.compile_class_var_dec()
            elif self.token.get_token_value() in ('constructor', 'function', 'method'):
                self.compile_subroutine_dec()
            else:
                print('error in compileClass()\n')
                sys.exit(1)

        self.process_token_expecting_value('}')
        self.write_xml_non_terminal('class', 'end')

    def compile_class_var_dec(self):
        self.write_xml_non_terminal('classVarDec', 'begin')

        self.write_xml_terminal()
        self.token.advance()
        self.expect_token_type('IDENTIFIER', 'KEYWORD')

        if self.token.get_token_type() == 'KEYWORD':
            self.expect_token_value('int', 'char', 'boolean')

        self.write_xml_terminal()
        self.token.advance()
        self.process_token_expecting_type('IDENTIFIER')

        while self.token.get_token_value() != ';':
            self.process_token_expecting_value(',')
            self.process_token_expecting_type('IDENTIFIER')

        self.write_xml_terminal()
        self.token.advance()
        self.write_xml_non_terminal('classVarDec', 'end')

    def compile_subroutine_dec(self):
        self.write_xml_non_terminal('subroutineDec', 'begin')

        self.write_xml_terminal()
        self.token.advance()
        self.expect_token_type('IDENTIFIER', 'KEYWORD')

        if self.token.get_token_type() == 'KEYWORD':
            self.expect_token_value('void', 'int', 'char', 'boolean')

        self.write_xml_terminal()
        self.token.advance()
        self.process_token_expecting_type('IDENTIFIER')
        self.process_token_expecting_value('(')
        self.compile_parameter_list()
        self.process_token_expecting_value(')')
        self.write_xml_non_terminal('subroutineBody', 'begin')
        self.process_token_expecting_value('{')

        while self.token.get_token_value() == 'var':
            self.compile_var_dec()

        if self.token.get_token_value() != '}':
            self.compile_statements()

        self.process_token_expecting_value('}')
        self.write_xml_non_terminal('subroutineBody', 'end')
        self.write_xml_non_terminal('subroutineDec', 'end')

    def compile_parameter_list(self):
        self.write_xml_non_terminal('parameterList', 'begin')

        while self.token.get_token_value() != ')':
            self.expect_token_type('IDENTIFIER', 'KEYWORD')

            if self.token.get_token_type() == 'KEYWORD':
                self.expect_token_value('void', 'int', 'char', 'boolean')

            self.write_xml_terminal()
            self.token.advance()
            self.process_token_expecting_type('IDENTIFIER')

            while self.token.get_token_value() != ')':
                self.process_token_expecting_value(',')
                self.expect_token_type('IDENTIFIER', 'KEYWORD')

                if self.token.get_token_type() == 'KEYWORD':
                    self.expect_token_value('void', 'int', 'char', 'boolean')

                self.write_xml_terminal()
                self.token.advance()
                self.process_token_expecting_type('IDENTIFIER')

        self.write_xml_non_terminal('parameterList', 'end')

    def compile_subroutine_body(self, subroutine_name=None):
        if subroutine_name:
            self.xml.write('\t' * self.tabk + '<identifier> ' + str(subroutine_name) + ' </identifier>\n')
        else:
            self.write_xml_terminal()
            self.token.advance()

        if self.token.get_token_value() == '.':
            self.write_xml_terminal()
            self.token.advance()
            self.process_token_expecting_type('IDENTIFIER')

        self.process_token_expecting_value('(')
        self.compile_expression_list()
        self.process_token_expecting_value(')')

    def compile_var_dec(self):
        self.write_xml_non_terminal('varDec', 'begin')
        self.write_xml_terminal()
        self.token.advance()
        self.expect_token_type('IDENTIFIER', 'KEYWORD')

        if self.token.get_token_type() == 'KEYWORD':
            self.expect_token_value('int', 'char', 'boolean')

        self.write_xml_terminal()
        self.token.advance()
        self.process_token_expecting_type('IDENTIFIER')

        while self.token.get_token_value() != ';':
            self.process_token_expecting_value(',')
            self.process_token_expecting_type('IDENTIFIER')

        self.write_xml_terminal()
        self.token.advance()
        self.write_xml_non_terminal('varDec', 'end')

    def compile_statements(self):
        self.write_xml_non_terminal('statements', 'begin')

        while self.token.get_token_value() != '}':
            if self.token.get_token_value() == 'let':
                self.compile_let_statement()
            elif self.token.get_token_value() == 'if':
                self.compile_if_statement()
            elif self.token.get_token_value() == 'while':
                self.compile_while_statement()
            elif self.token.get_token_value() == 'do':
                self.compile_do_statement()
            elif self.token.get_token_value() == 'return':
                self.compile_return_statement()
            else:
                print('error in compileStatements()\n')
                sys.exit(1)

        self.write_xml_non_terminal('statements', 'end')

    def compile_while_statement(self):
        self.write_xml_non_terminal('whileStatement', 'begin')
        self.write_xml_terminal()
        self.token.advance()
        self.process_token_expecting_value('(')
        self.compile_expression()
        self.process_token_expecting_value(')')
        self.process_token_expecting_value('{')
        self.compile_statements()
        self.process_token_expecting_value('}')
        self.write_xml_non_terminal('whileStatement', 'end')

    def compile_if_statement(self):
        self.write_xml_non_terminal('ifStatement', 'begin')
        self.write_xml_terminal()
        self.token.advance()
        self.process_token_expecting_value('(')
        self.compile_expression()
        self.process_token_expecting_value(')')
        self.process_token_expecting_value('{')
        self.compile_statements()
        self.process_token_expecting_value('}')

        if self.token.get_token_value() == 'else':
            self.write_xml_terminal()
            self.token.advance()
            self.process_token_expecting_value('{')
            self.compile_statements()
            self.process_token_expecting_value('}')

        self.write_xml_non_terminal('ifStatement', 'end')

    def compile_return_statement(self):
        self.write_xml_non_terminal('returnStatement', 'begin')
        self.write_xml_terminal()
        self.token.advance()

        if self.token.get_token_value() != ';':
            self.compile_expression()

        self.process_token_expecting_value(';')
        self.write_xml_non_terminal('returnStatement', 'end')

    def compile_let_statement(self):
        self.write_xml_non_terminal('letStatement', 'begin')
        self.write_xml_terminal()
        self.token.advance()
        self.process_token_expecting_type('IDENTIFIER')
        self.expect_token_value('[', '=')

        if self.token.get_token_value() == '[':
            self.write_xml_terminal()
            self.token.advance()
            self.compile_expression()
            self.process_token_expecting_value(']')

        self.write_xml_terminal()
        self.token.advance()
        self.compile_expression()
        self.process_token_expecting_value(';')
        self.write_xml_non_terminal('letStatement', 'end')

    def compile_do_statement(self):
        self.write_xml_non_terminal('doStatement', 'begin')
        self.write_xml_terminal()
        self.token.advance()
        self.compile_subroutine_body()
        self.process_token_expecting_value(';')
        self.write_xml_non_terminal('doStatement', 'end')

    def compile_expression(self):
        self.write_xml_non_terminal('expression', 'begin')
        self.compile_term()

        while self.token.get_token_value() in ('+', '-', '*', '/', '&', '|', '<', '>', '='):
            self.write_xml_terminal()
            self.token.advance()
            self.compile_term()

        self.write_xml_non_terminal('expression', 'end')

    def compile_term(self):
        self.write_xml_non_terminal('term', 'begin')

        if self.token.get_token_type() == 'IDENTIFIER':
            hold_name = self.token.get_token_value()
            self.token.advance()

            if self.token.get_token_value() in ('(', '.'):
                self.compile_subroutine_body(hold_name)
            elif self.token.get_token_value() == '[':
                self.xml.write('\t' * self.tabk + '<identifier> ' + str(hold_name) + ' </identifier>\n')
                self.write_xml_terminal()
                self.token.advance()
                self.compile_expression()
                self.process_token_expecting_value(']')
            else:
                self.xml.write('\t' * self.tabk + '<identifier> ' + str(hold_name) + ' </identifier>\n')

        elif self.token.get_token_type() == 'SYMBOL':
            if self.token.get_token_value() in ('-', '~'):
                self.write_xml_terminal()
                self.token.advance()
                self.compile_term()
            elif self.token.get_token_value() == '(':
                self.write_xml_terminal()
                self.token.advance()
                self.compile_expression()
                self.process_token_expecting_value(')')
        else:
            self.write_xml_terminal()
            self.token.advance()

        self.write_xml_non_terminal('term', 'end')

    def compile_expression_list(self):
        self.write_xml_non_terminal('expressionList', 'begin')

        if self.token.get_token_value() != ')':
            self.compile_expression()
            while self.token.get_token_value() != ')':
                self.process_token_expecting_value(',')
                self.compile_expression()

        self.write_xml_non_terminal('expressionList', 'end')


def main():
    if sys.argv[0] is None or sys.argv[1] is None or len(sys.argv) > 2:
        print("ERROR: Invalid input")
        print("USAGE: JackAnalyzer.py <.jack file path>")
        sys.exit(1)

    path = sys.argv[1]
    output = sys.argv[1].split("/")

    jack_files = []

    if not path.endswith(".jack"):
        print("ERROR: file is not a .jack file")
        sys.exit(1)
    else:
        jack_files.append(path)

    for file in jack_files:
        Parser(Tokenizer(file))

    print("FINISHED")
    print("xml files saved to directory " + output[0] + "/xml")


if __name__ == '__main__':
    main()
