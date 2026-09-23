from app.rag.models import Chunk
ORDER={"PUBLIC":0,"INTERNAL":1,"RESTRICTED":2}
def filter_authorized(chunks, access_level):
    level=ORDER.get(access_level,0)
    return [c for c in chunks if ORDER.get(c.access_level,0)<=level]
