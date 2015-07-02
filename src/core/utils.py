import os
import xml.parsers.expat, sys

def is_xml(xml_path):
    if os.path.splitext(xml_path)[1].strip().lower() == ".xml":
        try:
            parser = xml.parsers.expat.ParserCreate()
            parser.ParseFile(open(xml_path, "r"))
            return True
        except Exception:
            pass
    return False

def is_valid_xml(tid):
        # doc = models.Document.objects.get(task__pk=tid)
        # http://lxml.de/validation.html
        # find JATS NLM DTD on FS
        # from lxml import etree
        # parser = etree.XMLParser(dtd_validation=True)
        # dtd = etree.DTD(open(settings.DTD_FOO))
        # root = etree.XML(open(doc.file.path
    return False

# stolen from:
# http://stackoverflow.com/questions/10823877/what-is-the-fastest-way-to-flatten-arbitrarily-nested-lists-in-python
def flatten(container):
    for i in container:
        if isinstance(i, list) or isinstance(i, tuple):
            for j in flatten(i):
                yield j
        else:
            yield i
