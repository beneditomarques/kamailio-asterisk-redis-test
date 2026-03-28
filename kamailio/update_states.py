import KSR
import json
import time

redis_server = "reg_redis"

def mod_init():
    KSR.info("===== FROM PYTHON MOD INIT\n")
    return kamailio()

class kamailio:
    def __init__(self):
        KSR.info('===== kamailio.__init__\n')       
    
    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0
        
    def update_registration(self, msg):
        tenant = 'test.local'
        aor = KSR.pv.get("$fU") or KSR.pv.get("$rU")
        
        if aor is None:
            return 1

        try:
            expires_str = KSR.pv.get("$hdr(Expires)")
            expires     = int(expires_str) if expires_str else 0
        except (ValueError, TypeError):
            expires = 0
        

        # Criamos o dicionário de evento uma vez
        status = "registered" if expires > 0 else "not_registered"
        event_dict = {
            "event": "registration_update",
            "tenant": tenant,
            "extension": aor,
            "status": status,
            "expires": expires,
            "timestamp": int(time.time())
        }
        
        # separators=(',', ':') remove todos os espaços em branco do JSON
        event_json = json.dumps(event_dict, separators=(',', ':'))

        if expires > 0:
            # PUBLISH
            cmd_pub = f"PUBLISH voice_cache:registry-changes {event_json}"
            KSR.ndb_redis.redis_cmd(redis_server, cmd_pub, "r")          
            KSR.info(f"REG -> registered: {aor}\n")
        else:            
            # PUBLISH
            cmd_pub = f"PUBLISH voice_cache:registry-changes {event_json}"
            KSR.ndb_redis.redis_cmd(redis_server, cmd_pub, "r")
            KSR.info(f"REG -> not_registered: {aor}\n")

        return 1

    def update_peerstate(self, msg):           
        tenant    = 'test.local'
        peer      = KSR.pv.get("$avp(ps_peer)")
        old_state = KSR.pv.get("$avp(ps_prev_state)")
        new_state = KSR.pv.get("$avp(ps_state)")
        event_dict = {
            "event": "peerstate_update",
            "tenant": tenant,
            "extension": peer,
            "old_state": old_state,            
            "new_state": new_state,            
            "timestamp": int(time.time())
        }
        
        # separators=(',', ':') remove todos os espaços em branco do JSON
        event_json = json.dumps(event_dict, separators=(',', ':'))

        # PUBLISH
        cmd_pub = f"PUBLISH voice_cache:peerstate-changes {event_json}"
        KSR.ndb_redis.redis_cmd(redis_server, cmd_pub, "r")          
        KSR.info(f"PEER STATE ON {peer} CHANGED FROM {old_state} TO {new_state}\n")

        return 1    