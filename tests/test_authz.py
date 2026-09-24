from app.rag.models import Chunk
from app.security.authz import filter_authorized


def c(level):
    return Chunk("x" + level, "d", "d", "text", "url", "s", level, 0, 4)


def test_public_user_cannot_receive_internal_or_restricted():
    result = filter_authorized([c("PUBLIC"), c("INTERNAL"), c("RESTRICTED")], "PUBLIC")
    assert [x.access_level for x in result] == ["PUBLIC"]
