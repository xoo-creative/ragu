
from dataclasses import dataclass

@dataclass
class Page:

    """
    Contains information about a taipy page in the taipy app.

    url_path: the url path after '/' that you can find this page.
    page_name: the page name which shows on the menu bar
    """

    url_path: str
    page_name: str

    def convert_to_taipy_menu_page(self) -> tuple:
        return (self.url_path, self.page_name)
