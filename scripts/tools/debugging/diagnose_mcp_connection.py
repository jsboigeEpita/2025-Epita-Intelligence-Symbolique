import asyncio
import sys
import os

async def diagnose_mcp_connection():
    """
    Lance le serveur MCP et affiche en temps réel les sorties stdout et stderr
    pour diagnostiquer les problèmes de communication.
    """
    print("--- Lancement du diagnostic du serveur MCP ---")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "services.mcp_server.main",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )

    print(f"Serveur MCP lancé avec le PID : {process.pid}")

    async def read_stream(stream, prefix):
        while not stream.at_eof():
            line = await stream.readline()
            if line:
                print(f"[{prefix}] {line.decode('utf-8', errors='ignore').strip()}")
            else:
                break

    stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT"))
    stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR"))

    try:
        # Attendre un certain temps pour observer la sortie
        await asyncio.sleep(15)
    finally:
        print("\n--- Fin du diagnostic ---")
        if process.returncode is None:
            print("Le processus serveur est toujours en cours d'exécution. Terminaison...")
            process.terminate()
            await process.wait()
            print("Processus terminé.")
        else:
            print(f"Le processus serveur s'est terminé avec le code : {process.returncode}")

        stdout_task.cancel()
        stderr_task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(diagnose_mcp_connection())
