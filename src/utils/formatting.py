from bs4 import BeautifulSoup


def html_clean_summary(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")
    return text.strip()
