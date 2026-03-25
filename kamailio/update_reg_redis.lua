local redis_server = "reg_redis"

function update_registration()
    local tenant = "test.local"
    -- local aor    = KSR.pv.get("$au") or KSR.pv.get("$rU")
    local aor    = KSR.pv.get("$fU") or KSR.pv.get("$rU")
    if not aor then return end

    -- local expires = tonumber(KSR.pv.get("$expires")) or 0
    local expires = tonumber(KSR.pv.get("$hdr(Expires)")) or 0
    local key     = "voice_cache:tenant:" .. tenant .. ":extension:" .. aor

    if expires > 0 then
        KSR.ndb_redis.redis_cmd(redis_server, "SET", key, "registered", "EX", expires + 30)
        local event = string.format('{"event":"registration_update","tenant":"%s","extension":"%s","status":"registered","expires":%d,"timestamp":%d}', tenant, aor, expires, os.time())
        KSR.ndb_redis.redis_cmd(redis_server, "PUBLISH " .. "voice_cache:reg-changes " .. event, "r")
        KSR.info("REG -> registered: " .. aor .. "\n")
    else
        KSR.ndb_redis.redis_cmd(redis_server, "DEL", key)
        local event = string.format('{"event":"registration_update","tenant":"%s","extension":"%s","status":"unavailable","expires":0,"timestamp":%d}', tenant, aor, os.time())
        KSR.ndb_redis.redis_cmd(redis_server, "PUBLISH " .. "voice_cache:reg-changes " .. event, "r")
        KSR.info("REG -> unavailable: " .. aor .. "\n")
    end
end