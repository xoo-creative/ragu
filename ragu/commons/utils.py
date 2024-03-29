import pkg_resources
import fitz
import logging
import os


def load_text(path: str) -> str:
    """
    Load the text content from a file.

    Args:
        path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    logging.info(f"Reading from path {path}")
    with open(path, "r") as fp:
        return fp.read()
    
def load_prompt(prompt_file_name: str) -> str:

    prompt_path = pkg_resources.resource_filename(package_or_requirement="ragu", 
                                                  resource_name=f"prompts/{prompt_file_name}.txt")

    return load_text(prompt_path)

def clear(filepath: str) -> None:
    open(filepath, 'w').close()

def read_pdf(pdf_path:str):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc: 
        text += page.get_text().replace("\n", "")
    
    return text

def get_file_name(filepath: str) -> str:
    filename_ = os.path.basename(filepath)
    filename_split = filename_.split(".")
    if len(filename_split) == 2:
        ## first time uploading this file
        name_of_file, extension = filename_.split(".")[0], filename_.split(".")[1]
    else:
        name_of_file, extension = filename_.split(".")[0], filename_.split(".")[2]
    return f"{name_of_file}.{extension}"