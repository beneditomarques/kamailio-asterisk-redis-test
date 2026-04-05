import asyncio
import json
import redis.asyncio as redis
import os
from panoramisk import Manager

r = redis.Redis(host='redis', port=6379, decode_responses=True)

AMI_HOST = os.getenv('ASTERISK_SERVER', '127.0.0.1')
AMI_USER = os.getenv('ASTERISK_USER', 'admin')
AMI_PASS = os.getenv('ASTERISK_PASS', 'admin')

manager = None

# 🔒 controle de concorrência
semaphore = asyncio.Semaphore(20)

# 🔒 evita múltiplas sincronizações simultâneas
sync_running = False


# ---------------- AMI (PANORAMISK) ----------------

def handle_login(mngr: Manager):
    global sync_running

    print("🔁 AMI conectado/reconectado!", flush=True)

    if sync_running:
        print("⏳ Sync já em execução, ignorando...", flush=True)
        return

    sync_running = True

    try:        
        asyncio.create_task(sync_states_from_redis())
    finally:
        sync_running = False

async def connect_ami():
    global manager    

    while True:
        try:
            print("🔌 Conectando no AMI (Panoramisk)...", flush=True)

            manager = Manager(
                host=AMI_HOST,
                port=5038,
                username=AMI_USER,
                secret=AMI_PASS
            )
            manager.on_login = handle_login
            await manager.connect()

            print("✅ Conectado ao AMI!", flush=True)
            return

        except Exception as e:
            print(f"❌ Falha ao conectar no AMI: {e}", flush=True)
            await asyncio.sleep(3)


async def ami_send(tenant, extension, status):
    global manager

    try:
        if status == "registered":
            state = "NOT_INUSE"
        elif status in ["not_registered", "NA"]:
            state = "UNAVAILABLE"
        else:
            state = status

        custom = f"REG-{tenant}-{extension}"

        response = await manager.send_action({
            "Action": "Setvar",
            "Variable": f"DEVICE_STATE(Custom:{custom})",
            "Value": state
        })

        print(f"✓ Custom:{custom} = {state} | {response}", flush=True)

    except Exception as e:
        print(f"✗ Erro AMI: {e}", flush=True)


# ---------------- REDIS STATE ----------------

async def update_device_state(tenant, extension, *, state=None, registered=None):
    key = f"voice_cache:{tenant}:device_state:{extension}"

    try:
        pipe = r.pipeline()
        pipe.get(key)
        result = await pipe.execute()

        current = result[0]

        if current:
            data = json.loads(current)
        else:
            data = {
                "name": extension,
                "state": "UNKNOWN",
                "registered": "no"
            }

        if state is not None:
            data["state"] = state

        if registered is not None:
            data["registered"] = "yes" if registered else "no"

        await r.set(key, json.dumps(data))

        print(f"📝 Redis atualizado: {key} -> {data}", flush=True)

    except Exception as e:
        print(f"Erro ao atualizar Redis: {e}", flush=True)


# ---------------- REDIS → AMI SYNC ----------------

async def sync_states_from_redis():
    print("🔄 Sincronizando estados do Redis com Asterisk...", flush=True)

    try:
        cursor = 0

        while True:
            cursor, keys = await r.scan(
                cursor=cursor,
                match="voice_cache:*:device_state:*",
                count=100
            )

            for key in keys:
                value = await r.get(key)
                if not value:
                    continue

                try:
                    data = json.loads(value)

                    parts = key.split(":")
                    tenant = parts[1]
                    extension = parts[3]

                    state = data.get("state", "UNKNOWN")

                    asyncio.create_task(ami_send(tenant, extension, state))

                except Exception as e:
                    print(f"Erro ao processar {key}: {e}", flush=True)

            if cursor == 0:
                break

        print("✅ Sincronização concluída!", flush=True)

    except Exception as e:
        print(f"❌ Erro na sincronização: {e}", flush=True)


# ---------------- EVENT PROCESSOR ----------------

async def process_event(msg):
    async with semaphore:
        try:
            data = json.loads(msg['data'])
            tenant = data['tenant']
            ext = data['extension']

            if msg['channel'] == 'voice_cache:registry-changes':
                status = data['status']
                registered = (status == "registered")

                await update_device_state(
                    tenant,
                    ext,
                    registered=registered
                )

                asyncio.create_task(ami_send(tenant, ext, status))

            elif msg['channel'] == 'voice_cache:peerstate-changes':
                new_state = data['new_state']

                await update_device_state(
                    tenant,
                    ext,
                    state=new_state
                )

                asyncio.create_task(ami_send(tenant, ext, new_state))

        except Exception as e:
            print("Erro processamento:", e, flush=True)


# ---------------- LISTENER ----------------

async def listener():
    print("Iniciando...", flush=True)

    await connect_ami()

    pubsub = r.pubsub()
    await pubsub.subscribe(
        "voice_cache:registry-changes",
        "voice_cache:peerstate-changes"
    )

    print("🔥 Listener Redis iniciado...", flush=True)

    async for msg in pubsub.listen():
        if msg['type'] != 'message':
            continue

        asyncio.create_task(process_event(msg))


if __name__ == "__main__":
    asyncio.run(listener())