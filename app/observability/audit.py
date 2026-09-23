import json, logging, time, uuid
log=logging.getLogger("agentic-rag")
def audit_event(event, **fields):
    log.info(json.dumps({"event":event,"correlation_id":str(uuid.uuid4()),"ts":time.time(),**fields},default=str))
