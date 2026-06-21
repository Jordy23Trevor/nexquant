import re
import zipfile
import logging
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("epub_converter")

BOOKS_DIR = Path(__file__).parent / "books"

def convert_epub_to_txt(epub_path: Path):
    txt_path = epub_path.with_suffix(".txt")
    log.info(f"Extracting text from {epub_path.name} to {txt_path.name}...")
    
    text_content = []
    try:
        with zipfile.ZipFile(epub_path) as z:
            # Find and sort all html/xhtml documents inside the epub
            html_files = sorted([
                f for f in z.namelist() 
                if f.endswith((".html", ".xhtml", ".xml", ".htm"))
            ])
            
            for html_file in html_files:
                try:
                    content = z.read(html_file)
                    soup = BeautifulSoup(content, "html.parser")
                    text = soup.get_text()
                    # Clean up excessive newlines
                    text = re.sub(r"\n+", "\n", text).strip()
                    if text:
                        text_content.append(text)
                except Exception as e:
                    log.warning(f"Failed to read {html_file}: {e}")
                    
        if text_content:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(text_content))
            log.info(f"✅ Successfully converted: {txt_path.name}")
            
            # Rename the original epub file to have the correct extension (.epub) instead of .pdf
            correct_epub_path = epub_path.with_suffix(".epub")
            if not correct_epub_path.exists():
                epub_path.rename(correct_epub_path)
                log.info(f"Renamed original file to: {correct_epub_path.name}")
            else:
                epub_path.unlink()
                log.info(f"Deleted duplicate: {epub_path.name}")
            return True
        else:
            log.error(f"No text extracted from {epub_path.name}")
            return False
            
    except Exception as e:
        log.error(f"Failed to process ZIP/EPUB {epub_path.name}: {e}")
        return False

def main():
    log.info("Starting EPUB to TXT conversion...")
    for file_path in BOOKS_DIR.glob("*.pdf"):
        # Check if file has the ZIP/EPUB signature (PK..)
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                if header == b"PK\x03\x04":
                    convert_epub_to_txt(file_path)
        except Exception as e:
            log.error(f"Error checking file {file_path.name}: {e}")
            
    log.info("Conversion done.")

if __name__ == "__main__":
    main()
