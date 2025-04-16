from haystack import Pipeline
from haystack.components.converters import MarkdownToDocument
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.preprocessors import  RecursiveDocumentSplitter

def doc_splitter():
    splitter=RecursiveDocumentSplitter(
            split_length=220,
            split_overlap=20,
            split_unit="word",
            separators=["\n\n", "\n", "sentence", " "])
    p = Pipeline()
    p.add_component(instance=MarkdownToDocument(), name="md_file_converter")
    p.add_component(instance=DocumentCleaner(), name="cleaner")
    p.add_component(instance=splitter, name="splitter")
    p.connect("md_file_converter.documents", "cleaner.documents")
    p.connect("cleaner.documents", "splitter.documents")
    return p
