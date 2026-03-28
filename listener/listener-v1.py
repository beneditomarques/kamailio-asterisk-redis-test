import asyncio
import json
import redis.asyncio as redis
from asterisk.ami import AMIClient, SimpleAction
import os

r = redis.Redis(host='redis', port=6379, decode_responses=True)

async def ami_send(asterisk_host, tenant, extension, status):
    try:
        ami = AMIClient(address=asterisk_host,port=5038)
        ami.login(username='admin', secret='admin')
                
        if status == "registered":
            state = "NOT_INUSE"
        elif status == "not_registered":
            state = "UNAVAILABLE"
        elif status == "NA":
            state = "UNAVAILABLE"
        else:
            state = status

        custom = f"REG-{tenant}-{extension}"
        
        action = SimpleAction('Setvar',
                              Variable=f"DEVICE_STATE(Custom:{custom})",
                              Value=state)        
        future = ami.send_action(action)
        response = future.response

        print(f"✓ {asterisk_host} → Custom:{custom} = {state} | {response}")        
        future_logoff = ami.logoff()
        response_logoff = future_logoff.response
    except Exception as e:
        print(f"✗ Erro AMI {asterisk_host}: {e}")

async def listener():
    print("Iniciando...")
    pubsub = r.pubsub()
    await pubsub.subscribe(
        "voice_cache:registry-changes",
        "voice_cache:peerstate-changes"
    )
    print("🔥 Listener Redis iniciado...")

    async for msg in pubsub.listen():
        if msg['type'] == 'message':
            if msg['channel'] == 'voice_cache:registry-changes':
                try:
                    data = json.loads(msg['data'])
                    tenant = data['tenant']
                    ext    = data['extension']
                    status = data['status']
                                    
                    await ami_send(os.getenv('ASTERISK_SERVER','127.0.0.1'), tenant, ext, status)                
                except Exception as e:
                    print("Erro JSON:", e)
            
            if msg['channel'] == 'voice_cache:peerstate-changes':
                try:
                    data = json.loads(msg['data'])
                    tenant = data['tenant']
                    ext    = data['extension']
                    new_state = data['new_state']
                                    
                    await ami_send(os.getenv('ASTERISK_SERVER','127.0.0.1'), tenant, ext, new_state)                
                except Exception as e:
                    print("Erro JSON:", e)
            
if __name__ == "__main__":
    asyncio.run(listener())