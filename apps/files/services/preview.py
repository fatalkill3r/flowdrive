import csv, io, json
from .metadata import IMAGES, AUDIO, VIDEOS
from .storage import open_file
TEXT={"txt","log","csv","json","xml","md"}; MAX=512*1024
def preview_kind(item):
    ext=item.extension.lower()
    if ext in IMAGES:return "image"
    if ext=="pdf":return "pdf"
    if ext in AUDIO:return "audio"
    if ext in VIDEOS:return "video"
    if ext in TEXT:return ext if ext in ("csv","json") else "text"
    return "unsupported"
def text_content(item):
    with open_file(item) as stream: raw=stream.read(MAX)
    text=raw.decode("utf-8",errors="replace")
    if item.extension=="json":
        try:return json.dumps(json.loads(text),indent=2)
        except ValueError:return text
    return text
def csv_rows(item):
    return list(csv.reader(io.StringIO(text_content(item))))[:100]
