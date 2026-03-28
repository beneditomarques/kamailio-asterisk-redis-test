import asyncio
import json
import redis.asyncio as redis
from asterisk.ami import AMIClient, SimpleAction
import os

r = redis.Redis(host='redis', port=6379, decode_responses=True)

AMI_HOST = os.getenv('ASTERISK_SERVER', '127.0.0.1')
AMI_USER = os.getenv('ASTERISK_USER', 'admin')
AMI_PASS = os.getenv('ASTERISK_PASS', 'admin')

ami = None

# 🔥 LIMITE DE CONCORRÊNCIA
semaphore = asyncio.Semaphore(20)


# ---------------- AMI ----------------

async def connect_ami():
    global ami

    while True:
        try:
            print("🔌 Conectando no AMI...", flush=True)
            ami = AMIClient(address=AMI_HOST, port=5038)
            ami.login(username=AMI_USER, secret=AMI_PASS)

            print("✅ Conectado ao AMI!", flush=True)

            asyncio.create_task(sync_states_from_redis())

            return

        except Exception as e:
            print(f"❌ Falha ao conectar no AMI: {e}", flush=True)
            await asyncio.sleep(3)


async def ami_send(tenant, extension, status):
    global ami

    try:
        if status == "registered":
            state = "NOT_INUSE"
        elif status in ["not_registered", "NA"]:
            state = "UNAVAILABLE"
        else:
            state = status

        custom = f"REG-{tenant}-{extension}"

        action = SimpleAction(
            'Setvar',
            Variable=f"DEVICE_STATE(Custom:{custom})",
            Value=state
        )

        future = ami.send_action(action)

        #asyncio.create_task(handle_ami_response(future, custom, state))

    except Exception as e:
        print(f"✗ Erro AMI: {e}", flush=True)


async def handle_ami_response(future, custom, state):
    try:
        response = future.response
        print(f"✓ Custom:{custom} = {state} | {response}", flush=True)
    except Exception as e:
        print(f"Erro resposta AMI: {e}", flush=True)


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
    async with semaphore:  # 🔥 CONTROLE DE CONCORRÊNCIA
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