import re
from collections import namedtuple

CategoryDescription = namedtuple('CategoryDescription', ['description', 'url'])

block_exp = re.compile(r'\s*\n+\s*[>]{2}')
token_exp = re.compile(r'\s*[>]{2}\s*')
url_exp = re.compile(r'\s*[@]{2}\s*')
double_space_exp = re.compile(r'\s\s+')


def parse_category_description(description):
    """Parses the given description with the following format:

    >> Tagname >> Description @ External Address

    e.g.

    >> UN >> United Nations @@ www.un.org

    The description may have multiple lines.
    The part after the @@ is optional.

    Returns a dictionary like this:

    {'UN':
        CategoryDescription(
            description='United Nations', url='www.un.org'
        )
    }

    This may be viewed as temporary solution. Once we have an interface
    for defining descriptions to categories we can get rid of this.

    For now the user enters the descriptions in this syntax, which is
    of course easier than entering JSON, XML, YMAL, TOML and so on.
    """

    result = dict()

    if not description:
        return result

    clean = lambda s: re.sub(double_space_exp, u' ', s).strip(u' \n')
    split = lambda expr, text: (clean(t) for t in re.split(expr, text))

    for block in split(block_exp, description):

        if not block:
            continue

        # the first block may start with >> because the block expression
        # only works for splits in between
        if block.startswith('>>'):
            block = block[2:]

        category, desc = split(token_exp, block)

        if u'@@' in desc:
            desc, url = split(url_exp, desc)
        else:
            url = None

        result[category] = CategoryDescription(desc, url)

    return result


def valid_category_description(description):
    try:
        parse_category_description(description)
    except ValueError:
        return False

    return True
