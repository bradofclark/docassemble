import sys
import re
import os
import markdown
import mimetypes
import codecs
import json
import qrcode
import qrcode.image.svg
import StringIO
import tempfile
from docassemble.base.functions import server, word
from docassemble.base.pandoc import MyPandoc
from mdx_smartypants import SmartypantsExt
from bs4 import BeautifulSoup
import ruamel.yaml

from docassemble.base.logger import logmessage
from rtfng.object.picture import Image
import PIL

DEFAULT_PAGE_WIDTH = '6.5in'

smartyext = SmartypantsExt(configs=dict())
term_start = re.compile(r'\[\[')
term_match = re.compile(r'\[\[([^\]]*)\]\]')
noquote_match = re.compile(r'"')
lt_match = re.compile(r'<')
gt_match = re.compile(r'>')
amp_match = re.compile(r'&')
emoji_match = re.compile(r':([^ ]+):')
extension_match = re.compile(r'\.[a-z]+$')
map_match = re.compile(r'\[MAP ([^\]]+)\]', flags=re.DOTALL)
code_match = re.compile(r'<code>')

def set_default_page_width(width):
    global DEFAULT_PAGE_WIDTH
    DEFAULT_PAGE_WIDTH = str(width)
    return

def get_default_page_width():
    return(DEFAULT_PAGE_WIDTH)

DEFAULT_IMAGE_WIDTH = '4in'

def set_default_image_width(width):
    global DEFAULT_IMAGE_WIDTH
    DEFAULT_IMAGE_WIDTH = str(width)
    return

def get_default_image_width():
    return(DEFAULT_IMAGE_WIDTH)

MAX_HEIGHT_POINTS = 10 * 72

def set_max_height_points(points):
    global MAX_HEIGHT_POINTS
    MAX_HEIGHT_POINTS = points
    return

def get_max_height_points():
    return(MAX_HEIGHT_POINTS)

MAX_WIDTH_POINTS = 6.5 * 72.0

def set_max_width_points(points):
    global MAX_WIDTH_POINTS
    MAX_WIDTH_POINTS = points
    return

def get_max_width_points():
    return(MAX_WIDTH_POINTS)

# def blank_da_send_mail(*args, **kwargs):
#     logmessage("da_send_mail: no mail agent configured!")
#     return(None)

# da_send_mail = blank_da_send_mail

# def set_da_send_mail(func):
#     global da_send_mail
#     da_send_mail = func
#     return

# def blank_file_finder(*args, **kwargs):
#     return(dict(filename="invalid"))

# file_finder = blank_file_finder

# def set_file_finder(func):
#     global file_finder
#     #sys.stderr.write("set the file finder to " + str(func) + "\n")
#     file_finder = func
#     return

# def blank_url_finder(*args, **kwargs):
#     return('about:blank')

# url_finder = blank_url_finder

# def set_url_finder(func):
#     global url_finder
#     url_finder = func
#     return

# def blank_url_for(*args, **kwargs):
#     return('about:blank')

# url_for = blank_url_for

# def set_url_for(func):
#     global url_for
#     url_for = func
#     return

rtf_spacing = {'single': '\\sl0 ', 'oneandahalf': '\\sl360\\slmult1 ', 'double': '\\sl480\\slmult1 ', 'triple': '\\sl720\\slmult1 '}

rtf_after_space = {'single': 1, 'oneandahalf': 0, 'double': 0, 'triplespacing': 0}

def rtf_prefilter(text, metadata=dict()):
    text = re.sub(r'^# ', '[HEADING1] ', text, flags=re.MULTILINE)
    text = re.sub(r'^## ', '[HEADING2] ', text, flags=re.MULTILINE)
    text = re.sub(r'^### ', '[HEADING3] ', text, flags=re.MULTILINE)
    text = re.sub(r'^#### ', '[HEADING4] ', text, flags=re.MULTILINE)
    text = re.sub(r'^##### ', '[HEADING5] ', text, flags=re.MULTILINE)
    text = re.sub(r'^###### ', '[HEADING6] ', text, flags=re.MULTILINE)
    text = re.sub(r'^####### ', '[HEADING7] ', text, flags=re.MULTILINE)
    text = re.sub(r'^######## ', '[HEADING8] ', text, flags=re.MULTILINE)
    text = re.sub(r'^######### ', '[HEADING9] ', text, flags=re.MULTILINE)
    return(text)

def rtf_filter(text, metadata=None, styles=None, question=None):
    if metadata is None:
        metadata = dict()
    if styles is None:
        styles = dict()
    #sys.stderr.write(text + "\n")
    if 'fontsize' in metadata:
        text = re.sub(r'{\\pard', r'\\fs' + str(convert_length(metadata['fontsize'], 'hp')) + r' {\\pard', text, count=1)
        after_space_multiplier = str(convert_length(metadata['fontsize'], 'twips'))
    else:
        after_space_multiplier = 240
    if 'IndentationAmount' in metadata:
        indentation_amount = str(convert_length(metadata['IndentationAmount'], 'twips'))
    else:
        indentation_amount = '720'
    if 'Indentation' in metadata:
        if metadata['Indentation']:
            default_indentation = True
        else:
            default_indentation = False            
    else:
        default_indentation = True
    if 'SingleSpacing' in metadata and metadata['SingleSpacing']:
        #logmessage("Gi there!")
        default_spacing = 'single'
        if 'Indentation' not in metadata:
            default_indentation = False
    elif 'OneAndAHalfSpacing' in metadata and metadata['OneAndAHalfSpacing']:
        default_spacing = 'oneandahalf'
    elif 'DoubleSpacing' in metadata and metadata['DoubleSpacing']:
        default_spacing = 'double'
    elif 'TripleSpacing' in metadata and metadata['TripleSpacing']:
        default_spacing = 'triple'
    else:
        default_spacing = 'double'
    after_space = after_space_multiplier * rtf_after_space[default_spacing]
    text = re.sub(r'{\\pard \\ql \\f0 \\sa180 \\li0 \\fi0 \[HEADING([0-9]+)\] *', (lambda x: '{\\pard ' + styles.get(x.group(1), '\\ql \\f0 \\sa180 \\li0 \\fi0 ')), text)
    text = re.sub(r'{\\pard \\ql \\f0 \\sa180 \\li0 \\fi0 \[(BEGIN_TWOCOL|BREAK|END_TWOCOL|BEGIN_CAPTION|VERTICAL_LINE|END_CAPTION|SINGLESPACING|DOUBLESPACING|INDENTATION|NOINDENTATION|PAGEBREAK|SKIPLINE|FLUSHLEFT|FLUSHRIGHT|CENTER|BOLDCENTER|INDENTBY[^\]]*)\] *', r'[\1]{\\pard \\ql \\f0 \\sa180 \\li0 \\fi0 ', text)
    text = re.sub(r'{\\pard \\ql \\f0 \\sa180 \\li0 \\fi0 *\\par}', r'', text)
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'\[BEGIN_TWOCOL\](.+?)\[BREAK\]\s*(.+?)\[END_TWOCOL\]', rtf_caption_table, text, flags=re.DOTALL)
    text = re.sub(r'\[EMOJI ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_as_rtf(x, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_as_rtf(x, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+)\]', lambda x: image_as_rtf(x, question=question), text)
    text = re.sub(r'\[QR ([^,\]]+), *([0-9A-Za-z.%]+)\]', qr_as_rtf, text)
    text = re.sub(r'\[QR ([^\]]+)\]', qr_as_rtf, text)
    text = re.sub(r'\[MAP ([^\]]+)\]', '', text)
    text = re.sub(r'\[FIELD ([^\]]+)\]', '', text)
    text = re.sub(r'\[TARGET ([^\]]+)\]', '', text)
    text = re.sub(r'\[YOUTUBE ([^\]]+)\]', '', text)
    text = re.sub(r'\[VIMEO ([^\]]+)\]', '', text)
    text = re.sub(r'\[BEGIN_CAPTION\](.+?)\[VERTICAL_LINE\]\s*(.+?)\[END_CAPTION\]', rtf_caption_table, text)
    text = re.sub(r'\[NBSP\]', r'\\~ ', text)
    text = re.sub(r'\[ENDASH\]', r'{\\endash}', text)
    text = re.sub(r'\[EMDASH\]', r'{\\emdash}', text)
    text = re.sub(r'\[HYPHEN\]', r'-', text)
    text = re.sub(r'\[CHECKBOX\]', r'____', text)
    text = re.sub(r'\[BLANK\]', r'________________', text)
    text = re.sub(r'\[BLANKFILL\]', r'________________', text)
    text = re.sub(r'\[PAGEBREAK\] *', r'\\page ', text)
    text = re.sub(r'\[PAGENUM\]', r'{\\chpgn}', text)
    text = re.sub(r'\[TOTALPAGES\]', r'{\\nofpages3}', text)
    text = re.sub(r'\[SECTIONNUM\]', r'{\\sectnum}', text)
    text = re.sub(r' *\[SKIPLINE\] *', r'\\line ', text)
    text = re.sub(r' *\[NEWLINE\] *', r'\\line ', text)
    text = re.sub(r' *\[NEWPAR\] *', r'\\par ', text)
    text = re.sub(r' *\[BR\] *', r'\\line ', text)
    text = re.sub(r' *\[TAB\] *', r'\\tab ', text)
    # text = re.sub(r' *\[ENDFLUSHLEFT\] *', r'', text)
    # text = re.sub(r' *\[ENDFLUSHRIGHT\] *', r'', text)
    # text = re.sub(r' *\[ENDCENTER\] *', r'', text)
    # text = re.sub(r' *\[ENDBOLDCENTER\] *', r'', text)
    # text = re.sub(r' *\[ENDINDENTBY\] *', r'', text)
    # text = re.sub(r' *\[ENDBORDER\] *', r'', text)
    text = re.sub(r' *\[END\] *', r'\n', text)
    text = re.sub(r'\\sa180\\sa180\\par', r'\\par', text)
    text = re.sub(r'\\sa180', r'\\sa0', text)
    text = re.sub(r'(\\trowd \\trgaph[0-9]+)', r'\1\\trqc', text)
    text = re.sub(r'\\intbl\\row}\s*{\\pard', r'\\intbl\\row}\n\\line\n{\\pard', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\s*\[(SAVE|RESTORE|SINGLESPACING|DOUBLESPACING|TRIPLESPACING|ONEANDAHALFSPACING|INDENTATION|NOINDENTATION)\]\s*', r'\n[\1]\n', text)
    lines = text.split('\n')
    spacing_command = rtf_spacing[default_spacing]
    if default_indentation:
        indentation_command = r'\\fi' + str(indentation_amount) + " "
    else:
        indentation_command = r'\\fi0 '
    text = ''
    formatting_stack = list()
    for line in lines:
        if re.search(r'\[SAVE\]', line):
            formatting_stack.append(dict(spacing_command=spacing_command, after_space=after_space, default_indentation=default_indentation, indentation_command=indentation_command))
        elif re.search(r'\[RESTORE\]', line):
            if len(formatting_stack):
                prior_values = formatting_stack.pop()
                spacing_command = prior_values['spacing_command']
                after_space = prior_values['after_space']
                default_indentation = prior_values['default_indentation']
                indentation_command = prior_values['indentation_command']
        elif re.search(r'\[SINGLESPACING\]', line):
            spacing_command = rtf_spacing['single']
            after_space = after_space_multiplier * rtf_after_space[default_spacing]
            default_indentation = False
        elif re.search(r'\[ONEANDAHALFSPACING\]', line):
            spacing_command = rtf_spacing['oneandahalf']
            after_space = after_space_multiplier * rtf_after_space[default_spacing]
        elif re.search(r'\[DOUBLESPACING\]', line):
            spacing_command = rtf_spacing['double']
            after_space = after_space_multiplier * rtf_after_space[default_spacing]
        elif re.search(r'\[TRIPLESPACING\]', line):
            spacing_command = rtf_spacing['triple']
            after_space = after_space_multiplier * rtf_after_space[default_spacing]
        elif re.search(r'\[INDENTATION\]', line):
            indentation_command = r'\\fi' + str(indentation_amount) + " "
        elif re.search(r'\[NOINDENTATION\]', line):
            indentation_command = r'\\fi0 '
        elif line != '':
            if re.search(r'\[BORDER\]', line):
                line = re.sub(r' *\[BORDER\] *', r'', line)
                border_text = r'\\box \\brdrhair \\brdrw1 \\brdrcf1 \\brsp29 '
            else:
                border_text = r''
            line = re.sub(r'{(\\pard\\intbl \\q[lrc] \\f[0-9]+ \\sa[0-9]+ \\li[0-9]+ \\fi[0-9]+.*?)\\par}', r'\1', line)
            if re.search(r'\[NOPAR\]', line):
                line = re.sub(r'{\\pard \\ql \\f[0-9]+ \\sa[0-9]+ \\li[0-9]+ \\fi-?[0-9]* *(.*?)\\par}', r'\1', line)
                line = re.sub(r' *\[NOPAR\] *', r'', line)
            n = re.search(r'\[INDENTBY *([0-9\.]+ *[A-Za-z]+) *([0-9\.]+ *[A-Za-z]+)\]', line)
            m = re.search(r'\[INDENTBY *([0-9\.]+ *[A-Za-z]+)\]', line)
            if n:
                line = re.sub(r'\\fi-?[0-9]+ ', r'\\fi0 ', line)
                line = re.sub(r'\\ri-?[0-9]+ ', r'', line)
                line = re.sub(r'\\li-?[0-9]+ ', r'\\li' + str(convert_length(n.group(1), 'twips')) + r' \\ri' + str(convert_length(n.group(2), 'twips')) + ' ', line)
                line = re.sub(r'\[INDENTBY[^\]]*\]', '', line)
            if m:
                line = re.sub(r'\\fi-?[0-9]+ ', r'\\fi0 ', line)
                line = re.sub(r'\\li-?[0-9]+ ', r'\\li' + str(convert_length(m.group(1), 'twips')) + ' ', line)
                line = re.sub(r' *\[INDENTBY[^\]]*\] *', '', line)
            elif re.search(r'\[FLUSHLEFT\]', line):
                #sys.stderr.write("Flushleft line is: " + line + "\n")
                line = re.sub(r'\\fi-?[0-9]+ ', r'\\fi0 ', line)
                line = re.sub(r' *\[FLUSHLEFT\] *', '', line)
            elif re.search(r'\[FLUSHRIGHT\]', line):
                #sys.stderr.write("Flushright line is: " + line + "\n")
                line = re.sub(r'\\fi-?[0-9]+ ', r'\\fi0 ', line)
                line = re.sub(r'\\ql', r'\\qr', line)
                line = re.sub(r' *\[FLUSHRIGHT\] *', '', line)
            elif re.search(r'\[CENTER\]', line):
                line = re.sub(r'\\fi-?[0-9]+ ', r'\\fi0 ', line)
                line = re.sub(r'\\ql', r'\\qc', line)
                line = re.sub(r' *\[CENTER\] *', '', line)
            elif re.search(r'\[BOLDCENTER\]', line):
                line = re.sub(r'\\fi-?[0-9]+ ', r'\\fi0 ', line)
                line = re.sub(r'\\ql', r'\\qc \\b', line)
                line = re.sub(r' *\[BOLDCENTER\] *', '', line)
            elif indentation_command != '' and not re.search(r'\\widctlpar', line):
                line = re.sub(r'\\fi-?[0-9]+ ', indentation_command, line)
            if not re.search(r'\\s[0-9]', line):
                line = re.sub(r'\\pard ', r'\\pard ' + str(spacing_command) + str(border_text), line)
                line = re.sub(r'\\pard\\intbl ', r'\\pard\\intbl ' + str(spacing_command) + str(border_text), line)
            if not (re.search(r'\\fi0\\(endash|bullet)', line) or re.search(r'\\s[0-9]', line) or re.search(r'\\intbl', line)):
                if after_space > 0:
                    line = re.sub(r'\\sa[0-9]+ ', r'\\sa' + str(after_space) + ' ', line)
                else:
                    line = re.sub(r'\\sa[0-9]+ ', r'\\sa0 ', line)
            text += line + '\n'
    text = re.sub(r'{\\pard \\sl[0-9]+\\slmult[0-9]+ \\ql \\f[0-9]+ \\sa[0-9]+ \\li[0-9]+ \\fi-?[0-9]*\s*\\par}', r'', text)
    #text = re.sub(r'{\\pard \\sl[0-9]+\\slmult[0-9]+ \\ql \\f[0-9]+ \\sa[0-9]+ \\li[0-9]+ \\fi-?[0-9]*\s*\[FLUSHLEFT\]}', r'', text)
    return(text)

def docx_filter(text, metadata=None, question=None):
    if metadata is None:
        metadata = dict()
    text = text + "\n\n"
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'\[EMOJI ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_include_docx(x, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_include_docx(x, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+)\]', lambda x: image_include_docx(x, question=question), text)
    text = re.sub(r'\[QR ([^,\]]+), *([0-9A-Za-z.%]+)\]', qr_include_docx, text)
    text = re.sub(r'\[QR ([^\]]+)\]', qr_include_docx, text)
    text = re.sub(r'\[MAP ([^\]]+)\]', '', text)
    text = re.sub(r'\[FIELD ([^\]]+)\]', '', text)
    text = re.sub(r'\[TARGET ([^\]]+)\]', '', text)
    text = re.sub(r'\[YOUTUBE ([^\]]+)\]', '', text)
    text = re.sub(r'\[VIMEO ([^\]]+)\]', '', text)
    text = re.sub(r'\\clearpage *\\clearpage', '', text)
    text = re.sub(r'\[INDENTATION\]', '', text)
    text = re.sub(r'\[NOINDENTATION\]', '', text)    
    text = re.sub(r'\[BEGIN_CAPTION\](.+?)\[VERTICAL_LINE\]\s*(.+?)\[END_CAPTION\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[BEGIN_TWOCOL\](.+?)\[BREAK\]\s*(.+?)\[END_TWOCOL\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[SINGLESPACING\] *', '', text)
    text = re.sub(r'\[DOUBLESPACING\] *', '', text)
    text = re.sub(r'\[ONEANDAHALFSPACING\] *', '', text)
    text = re.sub(r'\[TRIPLESPACING\] *', '', text)
    text = re.sub(r'\[NBSP\]', ' ', text)
    text = re.sub(r'\[ENDASH\]', '--', text)
    text = re.sub(r'\[EMDASH\]', '---', text)
    text = re.sub(r'\[HYPHEN\]', '-', text)
    text = re.sub(r'\[CHECKBOX\]', '____', text)
    text = re.sub(r'\[BLANK\]', r'__________________', text)
    text = re.sub(r'\[BLANKFILL\]', r'__________________', text)
    text = re.sub(r'\[PAGEBREAK\] *', '', text)
    text = re.sub(r'\[PAGENUM\] *', '', text)
    text = re.sub(r'\[TOTALPAGES\] *', '', text)
    text = re.sub(r'\[SECTIONNUM\] *', '', text)
    text = re.sub(r'\[SKIPLINE\] *', '\n\n', text)
    text = re.sub(r'\[VERTICALSPACE\] *', '\n\n', text)
    text = re.sub(r'\[NEWLINE\] *', '\n\n', text)
    text = re.sub(r'\[NEWPAR\] *', '\n\n', text)
    text = re.sub(r'\[BR\] *', '\n\n', text)
    text = re.sub(r'\[TAB\] *', '', text)
    # text = re.sub(r'\[ENDFLUSHLEFT\]', r'\n\n', text)
    # text = re.sub(r'\[ENDFLUSHRIGHT\]', r'\n\n', text)
    # text = re.sub(r'\[ENDCENTER\]', r'\n\n', text)
    # text = re.sub(r'\[ENDBOLDCENTER\]', r'\n\n', text)
    # text = re.sub(r'\[ENDINDENTBY\]', r'\n\n', text)
    # text = re.sub(r'\[ENDBORDER\]', r'\n\n', text)
    text = re.sub(r' *\[END\] *', r'\n', text)
    text = re.sub(r'\[BORDER\] *(.+?)\n\n', r'\1\n\n', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[FLUSHLEFT\] *(.+?)\n\n', r'\1\n\n', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[FLUSHRIGHT\] *(.+?)\n\n', r'\1\n\n', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[CENTER\] *(.+?)\n\n', r'\1\n\n', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[BOLDCENTER\] *(.+?)\n\n', r'**\1**\n\n', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[INDENTBY *([0-9]+ *[A-Za-z]+)\] *(.+?)\n *\n', r'\2', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[INDENTBY *([0-9]+ *[A-Za-z]+) *([0-9]+ *[A-Za-z]+)\] *(.+?)\n *\n', r'\3', text, flags=re.MULTILINE | re.DOTALL)
    return(text)

def metadata_filter(text, doc_format):
    if doc_format == 'pdf':
        text = re.sub(r'\*\*([^\*]+?)\*\*', r'\\begingroup\\bfseries \1\\endgroup {}', text, flags=re.MULTILINE | re.DOTALL)
        text = re.sub(r'\*([^\*]+?)\*', r'\\begingroup\\itshape \1\\endgroup {}', text, flags=re.MULTILINE | re.DOTALL)
        text = re.sub(r'\_\_([^\_]+?)\_\_', r'\\begingroup\\bfseries \1\\endgroup {}', text, flags=re.MULTILINE | re.DOTALL)
        text = re.sub(r'\_([^\_]+?)\_*', r'\\begingroup\\itshape \1\\endgroup {}', text, flags=re.MULTILINE | re.DOTALL)
    return text

def pdf_filter(text, metadata=None, question=None):
    if metadata is None:
        metadata = dict()
    #if len(metadata):
    #    text = ruamel.yaml.dump(metadata) + "\n---\n" + text
    text = text + "\n\n"
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'\[EMOJI ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_include_string(x, emoji=True, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_include_string(x, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+)\]', lambda x: image_include_string(x, question=question), text)
    text = re.sub(r'\[QR ([^,\]]+), *([0-9A-Za-z.%]+)\]', qr_include_string, text)
    text = re.sub(r'\[QR ([^\]]+)\]', qr_include_string, text)
    text = re.sub(r'\[MAP ([^\]]+)\]', '', text)
    text = re.sub(r'\[FIELD ([^\]]+)\]', '', text)
    text = re.sub(r'\[TARGET ([^\]]+)\]', '', text)
    text = re.sub(r'\[YOUTUBE ([^\]]+)\]', '', text)
    text = re.sub(r'\[VIMEO ([^\]]+)\]', '', text)
    text = re.sub(r'\\clearpage *\\clearpage', r'\\clearpage', text)
    text = re.sub(r'\[BORDER\]\s*\[(BEGIN_TWOCOL|BEGIN_CAPTION|SINGLESPACING|DOUBLESPACING|INDENTATION|NOINDENTATION|FLUSHLEFT|FLUSHRIGHT|CENTER|BOLDCENTER|INDENTBY[^\]]*)\]', r'[\1] [BORDER]', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[INDENTATION\]', r'\\setlength{\\parindent}{0.5in}\\setlength{\\RaggedRightParindent}{\\parindent}', text)    
    text = re.sub(r'\[NOINDENTATION\]', r'\\setlength{\\parindent}{0in}\\setlength{\\RaggedRightParindent}{\\parindent}', text)    
    text = re.sub(r'\[BEGIN_CAPTION\](.+?)\[VERTICAL_LINE\]\s*(.+?)\[END_CAPTION\]', pdf_caption, text, flags=re.DOTALL)
    text = re.sub(r'\[BEGIN_TWOCOL\](.+?)\[BREAK\]\s*(.+?)\[END_TWOCOL\]', pdf_two_col, text, flags=re.DOTALL)
    text = re.sub(r'\[SINGLESPACING\]\s*', r'\\singlespacing\\setlength{\\parskip}{\\myfontsize}', text)
    text = re.sub(r'\[DOUBLESPACING\]\s*', r'\\doublespacing\\setlength{\\parindent}{0.5in}\\setlength{\\RaggedRightParindent}{\\parindent}', text)
    text = re.sub(r'\[ONEANDAHALFSPACING\]\s*', '\\onehalfspacing', text)
    text = re.sub(r'\[TRIPLESPACING\]\s*', '', text)
    text = re.sub(r'\[NBSP\]', r'\\myshow{\\nonbreakingspace}', text)
    text = re.sub(r'\[ENDASH\]', r'\\myshow{\\myendash}', text)
    text = re.sub(r'\[EMDASH\]', r'\\myshow{\\myemdash}', text)
    text = re.sub(r'\[HYPHEN\]', r'\\myshow{\\myhyphen}', text)
    text = re.sub(r'\[CHECKBOX\]', r'{\\rule{0.3in}{0.4pt}}', text)
    text = re.sub(r'\[BLANK\]', r'\\leavevmode{\\xrfill[-2pt]{0.4pt}}', text)
    text = re.sub(r'\[BLANKFILL\]', r'\\leavevmode{\\xrfill[-2pt]{0.4pt}}', text)
    text = re.sub(r'\[PAGEBREAK\]\s*', r'\\clearpage ', text)
    text = re.sub(r'\[PAGENUM\]', r'\myshow{\\thepage}', text)
    text = re.sub(r'\[TOTALPAGES\]', '\\myshow{\\pageref{LastPage}}', text)
    text = re.sub(r'\[SECTIONNUM\]', r'\\myshow{\\thesection}', text)
    text = re.sub(r'\[SKIPLINE\] *', r'\\par\\myskipline ', text)
    text = re.sub(r'\[VERTICALSPACE\] *', r'\\rule[-24pt]{0pt}{0pt}', text)
    text = re.sub(r'\[NEWLINE\] *', r'\\newline ', text)
    text = re.sub(r'\[NEWPAR\] *', r'\\par ', text)
    text = re.sub(r'\[BR\] *', r'\\manuallinebreak ', text)
    text = re.sub(r'\[TAB\] *', r'\\manualindent ', text)
    # text = re.sub(r'\[ENDFLUSHLEFT\]', r'\n\n', text)
    # text = re.sub(r'\[ENDFLUSHRIGHT\]', r'\n\n', text)
    # text = re.sub(r'\[ENDCENTER\]', r'\n\n', text)
    # text = re.sub(r'\[ENDBOLDCENTER\]', r'\n\n', text)
    # text = re.sub(r'\[ENDINDENTBY\]', r'\n\n', text)
    # text = re.sub(r'\[ENDBORDER\]', r'\n\n', text)
    text = re.sub(r' *\[END\] *', r'\n', text)
    text = re.sub(r'\[FLUSHLEFT\] *(.+?)\n *\n', flushleft_pdf, text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[FLUSHRIGHT\] *(.+?)\n *\n', flushright_pdf, text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[CENTER\] *(.+?)\n *\n', center_pdf, text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[BOLDCENTER\] *(.+?)\n *\n', boldcenter_pdf, text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[INDENTBY *([0-9]+ *[A-Za-z]+)\] *(.+?)\n *\n', indentby_left_pdf, text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[INDENTBY *([0-9]+ *[A-Za-z]+) *([0-9]+ *[A-Za-z]+)\] *(.+?)\n *\n', indentby_both_pdf, text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'\[BORDER\] *(.+?)\n *\n', border_pdf, text, flags=re.MULTILINE | re.DOTALL)
    return(text)

def html_filter(text, status=None, question=None, embedder=None):
    if question is None and status is not None:
        question = status.question
    text = text + "\n\n"
    text = re.sub(r'^[|] (.*)$', r'\1<br>', text, flags=re.MULTILINE)
    if embedder is not None:
        text = re.sub(r'\[FIELD ([^\]]+)\]', lambda x: embedder(status, x.group(1)), text)
    else:
        text = re.sub(r'\[FIELD ([^\]]+)\]', 'ERROR: FIELD cannot be used here', text)
    text = re.sub(r'\[TARGET ([^\]]+)\]', target_html, text)
    text = re.sub(r'\[EMOJI ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_url_string(x, emoji=True, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+), *([0-9A-Za-z.%]+)\]', lambda x: image_url_string(x, question=question), text)
    text = re.sub(r'\[FILE ([^,\]]+)\]', lambda x: image_url_string(x, question=question), text)
    text = re.sub(r'\[QR ([^,\]]+), *([0-9A-Za-z.%]+)\]', qr_url_string, text)
    text = re.sub(r'\[QR ([^,\]]+)\]', qr_url_string, text)
    if map_match.search(text):
        text = map_match.sub((lambda x: map_string(x.group(1), status)), text)
    text = re.sub(r'\[YOUTUBE ([^\]]+)\]', r'<iframe width="420" height="315" src="https://www.youtube.com/embed/\1" frameborder="0" allowfullscreen></iframe>', text)
    text = re.sub(r'\[VIMEO ([^\]]+)\]', r'<iframe src="https://player.vimeo.com/video/\1?byline=0&portrait=0" width="500" height="281" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>', text)
    text = re.sub(r'\[BEGIN_CAPTION\](.+?)\[VERTICAL_LINE\]\s*(.+?)\[END_CAPTION\]', html_caption, text)
    text = re.sub(r'\[BEGIN_TWOCOL\](.+?)\[BREAK\]\s*(.+?)\[END_TWOCOL\]', html_two_col, text, flags=re.DOTALL)
    text = re.sub(r'\[SINGLESPACING\] *', r'', text)
    text = re.sub(r'\[DOUBLESPACING\] *', r'', text)
    text = re.sub(r'\[ONEANDAHALFSPACING\] *', '', text)
    text = re.sub(r'\[TRIPLESPACING\] *', '', text)
    text = re.sub(r'\[INDENTATION\] *', r'', text)
    text = re.sub(r'\[NOINDENTATION\] *', r'', text)
    text = re.sub(r'\[NBSP\]', r'&nbsp;', text)
    text = re.sub(r'\[ENDASH\]', r'&ndash;', text)
    text = re.sub(r'\[EMDASH\]', r'&mdash;', text)
    text = re.sub(r'\[HYPHEN\]', r'-', text)
    text = re.sub(r'\[CHECKBOX\]', r'<span style="text-decoration: underline">&nbsp;&nbsp;&nbsp;&nbsp;</span>', text)
    text = re.sub(r'\[BLANK\]', r'<span style="text-decoration: underline">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>', text)
    text = re.sub(r'\[BLANKFILL\]', r'<span style="text-decoration: underline">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>', text)
    text = re.sub(r'\[PAGEBREAK\] *', r'', text)
    text = re.sub(r'\[PAGENUM\] *', r'', text)
    text = re.sub(r'\[SECTIONNUM\] *', r'', text)
    text = re.sub(r'\[SKIPLINE\] *', r'<br />', text)
    text = re.sub(r'\[NEWLINE\] *', r'<br />', text)
    text = re.sub(r'\[NEWPAR\] *', r'<br /><br />', text)
    text = re.sub(r'\[BR\] *', r'<br />', text)
    text = re.sub(r'\[TAB\] *', '<span class="datab"></span>', text)
    # text = re.sub(r'\[ENDFLUSHLEFT\]', r'\n\n', text)
    # text = re.sub(r'\[ENDFLUSHRIGHT\]', r'\n\n', text)
    # text = re.sub(r'\[ENDCENTER\]', r'\n\n', text)
    # text = re.sub(r'\[ENDBOLDCENTER\]', r'\n\n', text)
    # text = re.sub(r'\[ENDINDENTBY\]', r'\n\n', text)
    # text = re.sub(r'\[ENDBORDER\]', r'\n\n', text)
    text = re.sub(r' *\[END\] *', r'\n', text)
    lines = text.split('\n\n')
    text = ''
    for line in lines:
        classes = set()
        styles = dict()
        if re.search(r'\[BORDER\]', line):
            classes.add('daborder')
        if re.search(r'\[FLUSHLEFT\]', line):
            classes.add('daflushleft')
        if re.search(r'\[FLUSHRIGHT\]', line):
            classes.add('daflushright')
        if re.search(r'\[CENTER\]', line):
            classes.add('dacenter')
        if re.search(r'\[BOLDCENTER\]', line):
            classes.add('dacenter')
            classes.add('dabold')
        m = re.search(r'\[INDENTBY *([0-9]+ *[A-Za-z]+)\]', line)
        if m:
            styles["padding-left"] = str(convert_length(m.group(1), 'px')) + 'px'
        m = re.search(r'\[INDENTBY *([0-9]+ *[A-Za-z]+) *([0-9]+ *[A-Za-z]+)\]', line)
        if m:
            styles["margin-left"] = str(convert_length(m.group(1), 'px')) + 'px'
            styles["margin-right"] = str(convert_length(m.group(2), 'px')) + 'px'
        line = re.sub(r'\[(BORDER|FLUSHLEFT|FLUSHRIGHT|BOLDCENTER|CENTER)\] *', r'', line)
        line = re.sub(r'\[INDENTBY[^\]]*\]', r'', line)
        if len(classes) or len(styles):
            text += "<p"
            if len(classes):
                text += ' class="' + " ".join(classes) + '"'
            if len(styles):
                text += ' style="' + "".join(map(lambda x: str(x) + ":" + styles[x] + ';', styles.keys())) + '"'
            text += ">" + line + '</p>\n\n'
        else:
            text += line + '\n\n'
    text = re.sub(r'\\_', r'__', text)
    text = re.sub(r'\n+$', r'', text)
    return(text)

def clean_markdown_to_latex(string):
    string = re.sub(r'^[\n ]+', '', string)
    string = re.sub(r'[\n ]+$', '', string)
    string = re.sub(r' *\n *$', '\n', string)
    string = re.sub(r'\n{2,}', '[NEWLINE]', string)
    string = re.sub(r'\*\*([^\*]+?)\*\*', r'\\textbf{\1}', string)
    string = re.sub(r'\*([^\*]+?)\*', r'\\emph{\1}', string)
    string = re.sub(r'(?<!\\)_([^_]+?)_', r'\\emph{\1}', string)
    string = re.sub(r'\[([^\]]+?)\]\(([^\)]+?)\)', r'\\href{\2}{\1}', string)
    return string;

def map_string(encoded_text, status):
    if status is None:
        return ''
    map_number = len(status.maps)
    status.maps.append(codecs.decode(encoded_text, 'base64').decode('utf8'))
    return '<div id="map' + str(map_number) + '" class="googleMap"></div>'

def target_html(match):
    target = match.group(1)
    target = re.sub(r'[^A-Za-z0-9\_]', r'', str(target))
    return '<span id="datarget' + target + '"></span>'

def pdf_two_col(match, add_line=False):
    firstcol = clean_markdown_to_latex(match.group(1))
    secondcol = clean_markdown_to_latex(match.group(2))
    if add_line:
        return '\\noindent\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\mynoindent\\begin{tabular}{@{}m{0.49\\textwidth}|@{\\hspace{1em}}m{0.49\\textwidth}@{}}{' + firstcol + '} & {' + secondcol + '} \\\\ \\end{tabular}\\endgroup\\myskipline'
    else:
        return '\\noindent\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\mynoindent\\begin{tabular}{@{}p{0.49\\textwidth}@{\\hspace{1em}}p{0.49\\textwidth}@{}}{' + firstcol + '} & {' + secondcol + '} \\\\ \\end{tabular}\\endgroup\\myskipline'

def html_caption(match):
    firstcol = match.group(1)
    secondcol = match.group(2)
    return '<table style="width: 100%"><tr><td style="width: 50%; border-style: solid; border-right-width: 1px; padding-right: 1em; border-left-width: 0px; border-top-width: 0px; border-bottom-width: 0px">' + firstcol + '</td><td style="padding-left: 1em; width: 50%;">' + secondcol + '</td></tr></table>'

def html_two_col(match):
    firstcol = markdown_to_html(match.group(1))
    secondcol = markdown_to_html(match.group(2))
    return '<table style="width: 100%"><tr><td style="width: 50%; vertical-align: top; border-style: none; padding-right: 1em;">' + firstcol + '</td><td style="padding-left: 1em; vertical-align: top; width: 50%;">' + secondcol + '</td></tr></table>'

def pdf_caption(match):
    return pdf_two_col(match, add_line=True)

def add_newlines(string):
    string = re.sub(r'\[(BR)\]', r'[NEWLINE]', string)
    string = re.sub(r' *\n', r'\n', string)
    string = re.sub(r'(?<!\[NEWLINE\])\n', r' [NEWLINE]\n', string)
    return string    

def border_pdf(match):
    string = match.group(1)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    return('\\mdframed ' + unicode(string) + '\n\n\\endmdframed' + "\n\n")

def flushleft_pdf(match):
    string = match.group(1)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    return borderify('\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\setlength{\\parindent}{0pt}\\noindent ' + unicode(string) + '\\par\\endgroup') + "\n\n"

def flushright_pdf(match):
    string = match.group(1)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    return borderify('\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\setlength{\\parindent}{0pt}\\RaggedLeft ' + unicode(string) + '\\par\\endgroup') + "\n\n"

def center_pdf(match):
    string = match.group(1)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    return borderify('\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\Centering\\noindent ' + unicode(string) + '\\par\\endgroup') + "\n\n"

def boldcenter_pdf(match):
    string = match.group(1)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    return borderify('\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\Centering\\bfseries\\noindent ' + unicode(string) + '\\par\\endgroup') + "\n\n"

def indentby_left_pdf(match):
    string = match.group(2)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    if re.search(r'\[BORDER\]', string):
        string = re.sub(r' *\[BORDER\] *', r'', string)
        return '\\mdframed[leftmargin=' + str(convert_length(match.group(1), 'pt')) + 'pt]\n\\noindent ' + unicode(string) + '\n\n\\endmdframed' + "\n\n"
    return '\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\setlength{\\leftskip}{' + str(convert_length(match.group(1), 'pt')) + 'pt}\\noindent ' + unicode(string) + '\\par\\endgroup' + "\n\n"

def indentby_both_pdf(match):
    string = match.group(3)
    string = re.sub(r'\[NEWLINE\] *', r'\\newline ', string)
    if re.search(r'\[BORDER\]', string):
        string = re.sub(r' *\[BORDER\] *', r'', string)
        return '\\mdframed[leftmargin=' + str(convert_length(match.group(1), 'pt')) + 'pt,rightmargin=' + str(convert_length(match.group(2), 'pt')) + 'pt]\n\\noindent ' + unicode(string) + '\n\n\\endmdframed' + "\n\n"
    return '\\begingroup\\singlespacing\\setlength{\\parskip}{0pt}\\setlength{\\leftskip}{' + str(convert_length(match.group(1), 'pt')) + 'pt}\\setlength{\\rightskip}{' + str(convert_length(match.group(2), 'pt')) + 'pt}\\noindent ' + unicode(string) + '\\par\\endgroup' + "\n\n"

def borderify(string):
    if not re.search(r'\[BORDER\]', string):
        return string
    string = re.sub(r'\[BORDER\] *', r'', string)
    return('\\mdframed ' + unicode(string) + '\\endmdframed')

def image_as_rtf(match, question=None):
    width_supplied = False
    try:
        width = match.group(2)
        width_supplied = True
    except:
        width = DEFAULT_IMAGE_WIDTH
    if width == 'full':
        width_supplied = False
    file_reference = match.group(1)
    file_info = server.file_finder(file_reference, convert={'svg': 'png'}, question=question)
    if 'path' not in file_info:
        return ''
    #logmessage('image_as_rtf: path is ' + file_info['path'])
    if 'mimetype' in file_info:
        if re.search(r'^(audio|video)', file_info['mimetype']):
            return '[reference to file type that cannot be displayed]'
    if 'width' in file_info:
        return rtf_image(file_info, width, not width_supplied)
    elif file_info['extension'] == 'pdf':
        output = ''
        if not width_supplied:
            #logmessage("Adding page break\n")
            width = DEFAULT_PAGE_WIDTH
            output += '\\page '
        #logmessage("maxpage is " + str(int(file_info['pages'])) + "\n")
        max_pages = 1 + int(file_info['pages'])
        formatter = '%0' + str(len(str(max_pages))) + 'd'
        for page in range(1, max_pages):
            #logmessage("Doing page " + str(page) + "\n")
            page_file = dict()
            page_file['extension'] = 'png'
            page_file['path'] = file_info['path'] + 'page-' + formatter % page
            page_file['fullpath'] = page_file['path'] + '.png'
            im = PIL.Image.open(page_file['fullpath'])
            page_file['width'], page_file['height'] = im.size
            output += rtf_image(page_file, width, False)
            if not width_supplied:
                #logmessage("Adding page break\n")
                output += '\\page '
            else:
                output += ' '
        #logmessage("Returning output\n")
        return(output)
    else:
        return('')

def qr_as_rtf(match):
    width_supplied = False
    try:
        width = match.group(2)
        width_supplied = True
    except:
        width = DEFAULT_IMAGE_WIDTH
    if width == 'full':
        width_supplied = False
    string = match.group(1)
    output = ''
    if not width_supplied:
        #logmessage("Adding page break\n")
        width = DEFAULT_PAGE_WIDTH
        output += '\\page '
    im = qrcode.make(string)
    the_image = tempfile.NamedTemporaryFile(suffix=".png")
    im.save(the_image.name)
    page_file = dict()
    page_file['extension'] = 'png'
    page_file['fullpath'] = the_image.name    
    page_file['width'], page_file['height'] = im.size
    output += rtf_image(page_file, width, False)
    if not width_supplied:
        #logmessage("Adding page break\n")
        output += '\\page '
    else:
        output += ' '
    #logmessage("Returning output\n")
    return(output)

def rtf_image(file_info, width, insert_page_breaks):
    pixels = pixels_in(width)
    if pixels > 0 and file_info['width'] > 0:
        scale = float(pixels)/float(file_info['width'])
        #logmessage("scale is " + str(scale) + "\n")
        if scale*float(file_info['height']) > float(MAX_HEIGHT_POINTS):
            scale = float(MAX_HEIGHT_POINTS)/float(file_info['height'])
        #logmessage("scale is " + str(scale) + "\n")
        if scale*float(file_info['width']) > float(MAX_WIDTH_POINTS):
            scale = float(MAX_WIDTH_POINTS)/float(file_info['width'])
        #logmessage("scale is " + str(scale) + "\n")
        #scale *= 100.0
        #logmessage("scale is " + str(scale) + "\n")
        #scale = int(scale)
        #logmessage("scale is " + str(scale) + "\n")
        wtwips = int(scale*float(file_info['width'])*20.0)
        htwips = int(scale*float(file_info['height'])*20.0)
        image = Image( file_info['fullpath'] )
        image.Data = re.sub(r'\\picwgoal([0-9]+)', r'\\picwgoal' + str(wtwips), image.Data)
        image.Data = re.sub(r'\\pichgoal([0-9]+)', r'\\pichgoal' + str(htwips), image.Data)
    else:
        image = Image( file_info['fullpath'] )
    if insert_page_breaks:
        content = '\\page '
    else:
        content = ''
    return(content + image.Data)
    
unit_multipliers = {'twips': 0.0500, 'hp': 0.5, 'in': 72, 'pt': 1, 'px': 1, 'em': 12, 'cm': 28.346472}

def convert_length(length, unit):
    value = pixels_in(length)
    if unit in unit_multipliers:
        size = float(value)/float(unit_multipliers[unit])
        return(int(size))
    else:
        logmessage("Unit " + str(unit) + " is not a valid unit\n")
    return(300)
    
def pixels_in(length):
    m = re.search(r"([0-9.]+) *([a-z]+)", str(length).lower())
    if m:
        value = float(m.group(1))
        unit = m.group(2)
        #logmessage("value is " + str(value) + " and unit is " + unit + "\n")
        if unit in unit_multipliers:
            size = float(unit_multipliers[unit]) * value
            #logmessage("size is " + str(size) + "\n")
            return(int(size))
    logmessage("Could not read " + str(length) + "\n")
    return(300)

def image_url_string(match, emoji=False, question=None, playground=False):
    file_reference = match.group(1)
    try:
        width = match.group(2)
    except:
        width = "300px"
    if width == "full":
        width = "300px"    
    file_info = server.file_finder(file_reference, question=question)
    if 'mimetype' in file_info and file_info['mimetype'] is not None:
        if re.search(r'^audio', file_info['mimetype']):
            urls = get_audio_urls([{'text': "[FILE " + file_reference + "]", 'package': None, 'type': 'audio'}], question=question)
            if len(urls):
                return audio_control(urls)
            return ''
        if re.search(r'^video', file_info['mimetype']):
            urls = get_video_urls([{'text': "[FILE " + file_reference + "]", 'package': None, 'type': 'video'}], question=question)
            if len(urls):
                return video_control(urls)
            return ''
    if 'extension' in file_info and file_info['extension'] is not None:
        if re.match(r'.*%$', width):
            width_string = "width:" + width
        else:
            width_string = "max-width:" + width
        if emoji:
            width_string += ';vertical-align: middle'
        if file_info.get('extension', '') in ['png', 'jpg', 'gif', 'svg', 'jpe', 'jpeg']:
            return('<img class="daicon" style="' + width_string + '" src="' + server.url_finder(file_reference, question=question) + '"/>')
        elif file_info['extension'] == 'pdf':
            output = '<a href="' + server.url_finder(file_reference, question=question) + '"><img class="daicon" style="' + width_string + '" src="' + server.url_finder(file_reference, size="screen", page=1, question=question) + '"/></a>'
            if 'pages' in file_info and file_info['pages'] > 1:
                output += " (" + str(file_info['pages']) + " " + word('pages') + ")"
            return(output)
        else:
            return('<a href="' + server.url_finder(file_reference, question=question) + '">' + file_info['filename'] + '</a>')
    else:
        return('[Invalid image reference; reference=' + str(file_reference) + ', width=' + str(width) + ', filename=' + file_info.get('filename', 'unknown') + ']')

def qr_url_string(match):
    string = match.group(1)
    try:
        width = match.group(2)
    except:
        width = "300px"
    if width == "full":
        width = "300px"    
    width_string = "width:" + width
    im = qrcode.make(string, image_factory=qrcode.image.svg.SvgPathImage)
    output = StringIO.StringIO()
    im.save(output)
    the_image = output.getvalue()
    the_image = re.sub("<\?xml version='1.0' encoding='UTF-8'\?>\n", '', the_image)
    the_image = re.sub(r'height="[0-9]+mm" ', '', the_image)
    the_image = re.sub(r'width="[0-9]+mm" ', '', the_image)
    m = re.search(r'(viewBox="[^"]+")', the_image)
    if m:
        viewbox = m.group(1)
    else:
        viewbox = ""
    return('<svg style="' + width_string + '" ' + viewbox + '><g transform="scale(1.0)">' + the_image + '</g></svg>')

def convert_pixels(match):
    pixels = match.group(1)
    return (str(int(pixels)/72.0) + "in")

def image_include_string(match, emoji=False, question=None):
    file_reference = match.group(1)
    try:
        width = match.group(2)
        width = re.sub(r'^(.*)px', convert_pixels, width)
        if width == "full":
            width = '\\textwidth'
    except:
        width = DEFAULT_IMAGE_WIDTH
    file_info = server.file_finder(file_reference, convert={'svg': 'eps'}, question=question)
    if 'mimetype' in file_info:
        if re.search(r'^(audio|video)', file_info['mimetype']):
            return '[reference to file type that cannot be displayed]'
    if 'path' in file_info:
        if 'extension' in file_info:
            if file_info['extension'] in ['png', 'jpg', 'gif', 'pdf', 'eps', 'jpe', 'jpeg']:
                if file_info['extension'] == 'pdf':
                    output = '\\includepdf[pages={-}]{' + file_info['path'] + '.pdf}'
                else:
                    if emoji:
                        output = '\\raisebox{-.6\\dp\\strutbox}{\\mbox{\\includegraphics[width=' + width + ']{' + file_info['path'] + '}}}'
                    else:
                        output = '\\mbox{\\includegraphics[width=' + width + ']{' + file_info['path'] + '}}'
                    if width == '\\textwidth':
                        output = '\\clearpage ' + output + '\\clearpage '
                return(output)
    return('[invalid graphics reference]')

def image_include_docx(match, question=None):
    file_reference = match.group(1)
    try:
        width = match.group(2)
        width = re.sub(r'^(.*)px', convert_pixels, width)
        if width == "full":
            width = '100%'
    except:
        width = DEFAULT_IMAGE_WIDTH
    file_info = server.file_finder(file_reference, convert={'svg': 'eps'}, question=question)
    if 'mimetype' in file_info:
        if re.search(r'^(audio|video)', file_info['mimetype']):
            return '[reference to file type that cannot be displayed]'
    if 'path' in file_info:
        if 'extension' in file_info:
            if file_info['extension'] in ['png', 'jpg', 'gif', 'pdf', 'eps', 'jpe', 'jpeg']:
                output = '![](' + file_info['path'] + '){width=' + width + '}'
                return(output)
    return('[invalid graphics reference]')

def qr_include_string(match):
    string = match.group(1)
    try:
        width = match.group(2)
        width = re.sub(r'^(.*)px', convert_pixels, width)
        if width == "full":
            width = '\\textwidth'
    except:
        width = DEFAULT_IMAGE_WIDTH
    im = qrcode.make(string)
    the_image = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    im.save(the_image.name)
    output = '\\mbox{\\includegraphics[width=' + width + ']{' + the_image.name + '}}'
    if width == '\\textwidth':
        output = '\\clearpage ' + output + '\\clearpage '
    #logmessage("Output is " + output)
    return(output)

def qr_include_docx(match):
    string = match.group(1)
    try:
        width = match.group(2)
        width = re.sub(r'^(.*)px', convert_pixels, width)
        if width == "full":
            width = '100%'
    except:
        width = DEFAULT_IMAGE_WIDTH
    im = qrcode.make(string)
    the_image = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    im.save(the_image.name)
    output = '![](' + the_image.name + '){width=' + width + '}'
    return(output)

def rtf_caption_table(match):
    table_text = """\\trowd \\irow0\\irowband0\\lastrow \\ltrrow\\ts24\\trgaph108\\trleft0\\trbrdrt\\brdrs\\brdrw10 \\trbrdrl\\brdrs\\brdrw10 \\trbrdrb\\brdrs\\brdrw10 \\trbrdrr\\brdrs\\brdrw10 \\trbrdrh\\brdrs\\brdrw10 \\trbrdrv\\brdrs\\brdrw10 
\\trftsWidth1\\trftsWidthB3\\trftsWidthA3\\trautofit1\\trpaddl108\\trpaddr108\\trpaddfl3\\trpaddft3\\trpaddfb3\\trpaddfr3\\trcbpat1\\trcfpat1\\tblrsid1508006\\tbllkhdrrows\\tbllkhdrcols\\tbllknocolband\\tblind0\\tblindtype3 \\clvertalc\\clbrdrt\\brdrnone \\clbrdrl\\brdrnone 
\\clbrdrb\\brdrnone \\clbrdrr\\clshdng0\\brdrs\\brdrw10 \\cltxlrtb\\clftsWidth3\\clwWidth4732 \\cellx4680\\clvertalc\\clbrdrt\\brdrnone \\clbrdrl\\brdrs\\brdrw10 \\clbrdrb\\brdrnone \\clbrdrr\\clshdng0\\brdrnone \\cltxlrtb\\clftsWidth3\\clwWidth4732 \\cellx9468\\pard\\plain \\ltrpar
\\ql \\li0\\ri0\\widctlpar\\intbl\\wrapdefault\\aspalpha\\aspnum\\faauto\\adjustright\\rin0\\lin0\\pararsid1508006\\yts24 \\rtlch\\fcs1 \\af0\\afs22\\alang1025 \\ltrch\\fcs0 \\fs22\\lang1033\\langfe1033\\cgrid\\langnp1033\\langfenp1033 {\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0 \\insrsid2427490 [SAVE][SINGLESPACING][NOINDENTATION]""" + match.group(1) + """}{\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0 \\insrsid10753242\\charrsid2427490 \\cell }\\pard \\ltrpar
\\ql \\li162\\ri0\\widctlpar\\intbl\\wrapdefault\\aspalpha\\aspnum\\faauto\\adjustright\\rin0\\lin162\\pararsid15432102\\yts24 {\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0 \\li240 \\insrsid2427490 """ + match.group(2) + """[RESTORE]}{\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0 \\insrsid10753242\\charrsid2427490 \\cell }\\pard\\plain \\ltrpar
\\ql \\li0\\ri0\\sa200\\sl276\\slmult1\\widctlpar\\intbl\\wrapdefault\\aspalpha\\aspnum\\faauto\\adjustright\\rin0\\lin0 \\rtlch\\fcs1 \\af0\\afs22\\alang1025 \\ltrch\\fcs0 \\fs24\\lang1033\\langfe1033\\cgrid\\langnp1033\\langfenp1033 {\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0 \\insrsid10753242 
\\trowd \\irow0\\irowband0\\lastrow \\ltrrow\\ts24\\trgaph108\\trleft0\\trbrdrt\\brdrs\\brdrw10 \\trbrdrl\\brdrs\\brdrw10 \\trbrdrb\\brdrs\\brdrw10 \\trbrdrr\\brdrs\\brdrw10 \\trbrdrh\\brdrs\\brdrw10 \\trbrdrv\\brdrs\\brdrw10 
\\trftsWidth1\\trftsWidthB3\\trftsWidthA3\\trautofit1\\trpaddl108\\trpaddr108\\trpaddfl3\\trpaddft3\\trpaddfb3\\trpaddfr3\\trcbpat1\\trcfpat1\\tblrsid1508006\\tbllkhdrrows\\tbllkhdrcols\\tbllknocolband\\tblind0\\tblindtype3 \\clvertalc\\clbrdrt\\brdrnone \\clbrdrl\\brdrnone 
\\clbrdrb\\brdrnone \\clbrdrr\\clshdng0\\brdrs\\brdrw10 \\cltxlrtb\\clftsWidth3\\clwWidth4732 \\cellx4680\\clvertalc\\clbrdrt\\brdrnone \\clbrdrl\\brdrs\\brdrw10 \\clbrdrb\\brdrnone \\clbrdrr\\clshdng0\\brdrnone \\cltxlrtb\\clftsWidth3\\clwWidth4732 \\cellx9468\\row }"""
    table_text += """\\pard \\ltrpar
\\qc \\li0\\ri0\\sb0\\sl240\\slmult1\\widctlpar\\wrapdefault\\aspalpha\\aspnum\\faauto\\adjustright\\rin0\\lin0\\itap0\\pararsid10753242"""
    table_text = re.sub(r'\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0', r'\\rtlch\\fcs1 \\af0 \\ltrch\\fcs0 \\sl240 \\slmult1', table_text)
    return table_text

def emoji_html(text, status=None, images=None):
    if images is None:
        images = status.question.interview.images
    if text in images:
        if status is not None and images[text].attribution is not None:
            status.attributions.add(images[text].attribution)
        return("[EMOJI " + images[text].get_reference() + ', 1em]')
    else:
        return(":" + str(text) + ":")

def emoji_insert(text, status=None, images=None):
    if images is None:
        images = status.question.interview.images
    if text in images:
        if status is not None and images[text].attribution is not None:
            status.attributions.add(images[text].attribution)
        return("[EMOJI " + images[text].get_reference() + ', 1.2em]')
    else:
        return(":" + str(text) + ":")

def markdown_to_html(a, trim=False, pclass=None, status=None, question=None, use_pandoc=False, escape=False, do_terms=True, indent=None, strip_newlines=None, divclass=None, embedder=None):
    a = unicode(a)
    if question is None and status is not None:
        question = status.question
    if question is not None:
        if do_terms:
            if status is not None:
                if len(question.terms):
                    for term in question.terms:
                        a = question.terms[term]['re'].sub(r'[[\1]]', a)
                if len(question.autoterms):
                    for term in question.autoterms:
                        a = question.autoterms[term]['re'].sub(r'[[\1]]', a)
            if question.language in question.interview.terms and len(question.interview.terms[question.language]) > 0:
                for term in question.interview.terms[question.language]:
                    #logmessage("Searching for term " + term + " in " + a + "\n")
                    a = question.interview.terms[question.language][term]['re'].sub(r'[[\1]]', a)
                    #logmessage("string is now " + str(a) + "\n")
            if question.language in question.interview.autoterms and len(question.interview.autoterms[question.language]) > 0:
                for term in question.interview.autoterms[question.language]:
                    #logmessage("Searching for term " + term + " in " + a + "\n")
                    a = question.interview.autoterms[question.language][term]['re'].sub(r'[[\1]]', a)
                    #logmessage("string is now " + str(a) + "\n")
    if status is not None and len(question.interview.images) > 0:
        a = emoji_match.sub((lambda x: emoji_html(x.group(1), status=status)), a)
    a = html_filter(unicode(a), status=status, question=question, embedder=embedder)
    #logmessage("before: " + a)
    if use_pandoc:
        converter = MyPandoc()
        converter.output_format = 'html'
        #logmessage("input was:\n" + repr(a))
        converter.input_content = a
        converter.convert(question)
        result = converter.output_content.decode('utf8')
    else:
        result = markdown.markdown(a, extensions=[smartyext, 'markdown.extensions.sane_lists', 'markdown.extensions.tables'], output_format='html5')
    result = re.sub(r'<table>', r'<table class="table table-striped">', result)
    #result = re.sub(r'<table>', r'<table class="datable">', result)
    result = re.sub('<a href="(?!\?)', '<a target="_blank" href="', result)
    if do_terms and question is not None and term_start.search(result):
        if status is not None:
            if len(question.terms):
                result = term_match.sub((lambda x: add_terms(x.group(1), status.extras['terms'])), result)
            if len(question.autoterms):
                result = term_match.sub((lambda x: add_terms(x.group(1), status.extras['autoterms'])), result)
        if question.language in question.interview.terms and len(question.interview.terms[question.language]):
            result = term_match.sub((lambda x: add_terms(x.group(1), question.interview.terms[question.language])), result)
        if question.language in question.interview.autoterms and len(question.interview.autoterms[question.language]):
            result = term_match.sub((lambda x: add_terms(x.group(1), question.interview.autoterms[question.language])), result)
    if trim:
        if result.startswith('<p>') and result.endswith('</p>'):
            result = result[3:-4]
    elif pclass:
        result = re.sub('<p>', '<p class="' + pclass + '">', result)
    if escape:
        result = noquote_match.sub('&quot;', result)
        result = lt_match.sub('&lt;', result)
        result = gt_match.sub('&gt;', result)
        result = amp_match.sub('&amp;', result)
    #logmessage("after: " + result)
    #result = result.replace('\n', ' ')
    if result:
        if strip_newlines:
            result = result.replace('\n', ' ')
        if divclass is not None:
            result = '<div class="' + str(divclass) + '">' + result + '</div>'
        if indent and not code_match.search(result):
            return (" " * indent) + re.sub(r'\n', "\n" + (" " * indent), result).rstrip() + "\n"
    return(result)

def my_escape(result):
    result = noquote_match.sub('&quot;', result)
    result = lt_match.sub('&lt;', result)
    result = gt_match.sub('&gt;', result)
    result = amp_match.sub('&amp;', result)
    return(result)

def noquote(string):
    #return json.dumps(string.replace('\n', ' ').rstrip())
    return '"' + string.replace('\n', ' ').replace('"', '&quot;').rstrip() + '"'

def add_terms(termname, terms):
    lower_termname = termname.lower()
    if lower_termname in terms:
        return('<a class="daterm" data-toggle="popover" data-placement="bottom" data-content=' + noquote(terms[lower_termname]['definition']) + '>' + unicode(termname) + '</a>')
    else:
        #logmessage(lower_termname + " is not in terms dictionary\n")
        return '[[' + termname + ']]'

def audio_control(files, preload="metadata"):
    for d in files:
        if type(d) in (str, unicode):
            return d
    output = '<audio controls="controls" preload="' + preload + '">' + "\n"
    for d in files:
        if type(d) is list:
            output += '  <source src="' + d[0] + '"'
            if d[1] is not None:
                output += ' type="' + d[1] + '"/>'
            output += "\n"
    output += '  <a target="_blank" href="' + files[-1][0] +  '">' + word('Listen') + '</a>\n'
    output += "</audio>\n"
    return output

def video_control(files):
    for d in files:
        if type(d) in (str, unicode):
            return d
    output = '<video width="320" height="240" controls="controls">' + "\n"
    for d in files:
        if type(d) is list:
            output += '  <source src="' + d[0] + '"'
            if d[1] is not None:
                output += ' type="' + d[1] + '"/>'
            output += "\n"
    output += '  <a target="_blank" href="' + files[-1][0] +  '">' + word('Listen') + '</a>\n'
    output += "</video>\n"
    return output

def get_audio_urls(the_audio, question=None):
    output = list()
    the_list = list()
    to_try = dict()
    for audio_item in the_audio:
        if audio_item['type'] != 'audio':
            continue
        found_upload = False
        pattern = re.compile(r'^\[FILE ([^,\]]+)')
        for (file_ref) in re.findall(pattern, audio_item['text']):
            found_upload = True
            m = re.match(r'[0-9]+', file_ref)
            if m:
                file_info = server.file_finder(file_ref, question=question)
                if 'path' in file_info:
                    if file_info['mimetype'] == 'audio/ogg':
                        output.append([server.url_finder(file_ref, question=question), file_info['mimetype']])
                    elif os.path.isfile(file_info['path'] + '.ogg'):
                        output.append([server.url_finder(file_ref, ext='ogg', question=question), 'audio/ogg'])
                    if file_info['mimetype'] == 'audio/mpeg':
                        output.append([server.url_finder(file_ref, question=question), file_info['mimetype']])
                    elif os.path.isfile(file_info['path'] + '.mp3'):
                        output.append([server.url_finder(file_ref, ext='mp3', question=question), 'audio/mpeg'])
                    if file_info['mimetype'] not in ['audio/mpeg', 'audio/ogg']:
                        output.append([server.url_finder(file_ref, question=question), file_info['mimetype']])
            else:
                the_list.append({'text': file_ref, 'package': audio_item['package']})
        if not found_upload:
            the_list.append(audio_item)
    for audio_item in the_list:
        mimetype, encoding = mimetypes.guess_type(audio_item['text'])
        if re.search(r'^http', audio_item['text']):
            output.append([audio_item['text'], mimetype])
            continue
        basename = os.path.splitext(audio_item['text'])[0]
        ext = os.path.splitext(audio_item['text'])[1]
        if not mimetype in to_try:
            to_try[mimetype] = list();
        to_try[mimetype].append({'basename': basename, 'filename': audio_item['text'], 'ext': ext, 'package': audio_item['package']})
    if 'audio/mpeg' in to_try and 'audio/ogg' not in to_try:
        to_try['audio/ogg'] = list()
        for attempt in to_try['audio/mpeg']:
            if attempt['ext'] == '.MP3':
                to_try['audio/ogg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.OGG', 'ext': '.OGG', 'package': attempt['package']})
            else:
                to_try['audio/ogg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.ogg', 'ext': '.ogg', 'package': attempt['package']})
    if 'audio/ogg' in to_try and 'audio/mpeg' not in to_try:
        to_try['audio/mpeg'] = list()
        for attempt in to_try['audio/ogg']:
            if attempt['ext'] == '.OGG':
                to_try['audio/mpeg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.MP3', 'ext': '.MP3', 'package': attempt['package']})
            else:
                to_try['audio/mpeg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.mp3', 'ext': '.mp3', 'package': attempt['package']})
    for mimetype in reversed(sorted(to_try.iterkeys())):
        for attempt in to_try[mimetype]:
            parts = attempt['filename'].split(':')
            if len(parts) < 2:
                parts = [attempt['package'], attempt['filename']]
            if parts[0] is None:
                parts[0] = 'None'
            parts[1] = re.sub(r'^data/static/', '', parts[1])
            full_file = parts[0] + ':data/static/' + parts[1]
            file_info = server.file_finder(full_file, question=question)
            if 'fullpath' in file_info:
                url = server.url_finder(full_file, question=question)
                output.append([url, mimetype])
    return output

def get_video_urls(the_video, question=None):
    output = list()
    the_list = list()
    to_try = dict()
    for video_item in the_video:
        if video_item['type'] != 'video':
            continue
        found_upload = False
        if re.search(r'^\[(YOUTUBE|VIMEO) ', video_item['text']):
            output.append(html_filter(video_item['text']))
            continue
        pattern = re.compile(r'^\[FILE ([^,\]]+)')
        for (file_ref) in re.findall(pattern, video_item['text']):
            found_upload = True
            m = re.match(r'[0-9]+', file_ref)
            if m:
                file_info = server.file_finder(file_ref, question=question)
                if 'path' in file_info:
                    if file_info['mimetype'] == 'video/ogg':
                        output.append([server.url_finder(file_ref, question=question), file_info['mimetype']])
                    elif os.path.isfile(file_info['path'] + '.ogv'):
                        output.append([server.url_finder(file_ref, ext='ogv', question=question), 'video/ogg'])
                    if file_info['mimetype'] == 'video/mp4':
                        output.append([server.url_finder(file_ref, question=question), file_info['mimetype']])
                    elif os.path.isfile(file_info['path'] + '.mp4'):
                        output.append([server.url_finder(file_ref, ext='mp4', question=question), 'video/mp4'])
                    if file_info['mimetype'] not in ['video/mp4', 'video/ogg']:
                        output.append([server.url_finder(file_ref, question=question), file_info['mimetype']])
            else:
                the_list.append({'text': file_ref, 'package': video_item['package']})
        if not found_upload:
            the_list.append(video_item)
    for video_item in the_list:
        mimetype, encoding = mimetypes.guess_type(video_item['text'])
        if re.search(r'^http', video_item['text']):
            output.append([video_item['text'], mimetype])
            continue
        basename = os.path.splitext(video_item['text'])[0]
        ext = os.path.splitext(video_item['text'])[1]
        if not mimetype in to_try:
            to_try[mimetype] = list();
        to_try[mimetype].append({'basename': basename, 'filename': video_item['text'], 'ext': ext, 'package': video_item['package']})
    if 'video/mp4' in to_try and 'video/ogg' not in to_try:
        to_try['video/ogg'] = list()
        for attempt in to_try['audio/mp4']:
            if attempt['ext'] == '.MP4':
                to_try['video/ogg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.OGV', 'ext': '.OGV', 'package': attempt['package']})
            else:
                to_try['video/ogg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.ogv', 'ext': '.ogv', 'package': attempt['package']})
    if 'video/ogg' in to_try and 'video/mp4' not in to_try:
        to_try['video/mp4'] = list()
        for attempt in to_try['video/ogg']:
            if attempt['ext'] == '.OGV':
                to_try['video/mp4'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.MP4', 'ext': '.MP4', 'package': attempt['package']})
            else:
                to_try['audio/mpeg'].append({'basename': attempt['basename'], 'filename': attempt['basename'] + '.mp4', 'ext': '.mp4', 'package': attempt['package']})
    for mimetype in reversed(sorted(to_try.iterkeys())):
        for attempt in to_try[mimetype]:
            parts = attempt['filename'].split(':')
            if len(parts) < 2:
                parts = [attempt['package'], attempt['filename']]
            if parts[0] is None:
                parts[0] = 'None'
            parts[1] = re.sub(r'^data/static/', '', parts[1])
            full_file = parts[0] + ':data/static/' + parts[1]
            file_info = server.file_finder(full_file, question=question)
            if 'fullpath' in file_info:
                url = server.url_finder(full_file, question=question)
                output.append([url, mimetype])
    return output

def to_text(html_doc, terms, links, status):
    #url = status.current_info.get('url', 'http://localhost')
    #logmessage("url is " + str(url))
    output = ""
    #logmessage("to_text: html doc is " + str(html_doc))
    soup = BeautifulSoup(html_doc, 'html.parser')
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title', 'audio', 'video', 'pre', 'attribution'])]
    [s.extract() for s in soup.find_all(hidden)]
    [s.extract() for s in soup.find_all('div', {'class': 'invisible'})]
    for s in soup.find_all(do_show):
        if s.name in ['input', 'textarea', 'img'] and s.has_attr('alt'):
            words = s.attrs['alt']
            if s.has_attr('placeholder'):
                words += ", " + s.attrs['placeholder']
        else:
            words = s.get_text()
        words = re.sub(r'\n\s*', ' ', words, flags=re.DOTALL)
        output += words + "\n"
    for s in soup.find_all('a'):
        if s.has_attr('class') and s.attrs['class'][0] == 'daterm' and s.has_attr('data-content'):
            terms[s.string] = s.attrs['data-content']
        elif s.has_attr('href'):# and (s.attrs['href'].startswith(url) or s.attrs['href'].startswith('?')):
            #logmessage("Adding a link: " + s.attrs['href'])
            links.append((s.attrs['href'], s.get_text()))
    output = re.sub(ur'\u201c', '"', output)
    output = re.sub(ur'\u201d', '"', output)
    output = re.sub(ur'\u2018', "'", output)
    output = re.sub(ur'\u2019', "'", output)
    output = re.sub(ur'\u201b', "'", output)
    output = re.sub(r'&amp;gt;', '>', output)
    output = re.sub(r'&amp;lt;', '<', output)
    output = re.sub(r'&gt;', '>', output)
    output = re.sub(r'&lt;', '<', output)
    output = re.sub(r'<[^>]+>', '', output)
    output = re.sub(r'\n$', '', output)
    output = re.sub(r'  +', ' ', output)
    return output

bad_list = ['div', 'option']

good_list = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'button', 'textarea', 'note']

def do_show(element):
    if re.match('<!--.*-->', str(element), re.DOTALL):
        return False
    if element.name in ['option'] and element.has_attr('selected'):
        return True    
    if element.name in bad_list:
        return False
    if element.name in ['img', 'input'] and element.has_attr('alt'):
        return True
    if element.name in good_list:
        return True
    if element.parent and element.parent.name in good_list:
        return False
    if element.string:
        return True
    if re.match(r'\s+', element.get_text()):
        return False
    return False

def hidden(element):
    if element.name == 'input':
        if element.has_attr('type'):
            if element.attrs['type'] == 'hidden':
                return True
    return False
