from app.security.authz import filter_authorized
from app.rag.models import Chunk
def c(level): return Chunk("x","d","d","text","url","s",level,0,4)
def test_public_user_cannot_receive_internal():
    r=filter_authorized([c("PUBLIC"),c("INTERNAL"),c("RESTRICTED")],"PUBLIC")
    assert [x.access_level for x in r]==["PUBLIC"]
