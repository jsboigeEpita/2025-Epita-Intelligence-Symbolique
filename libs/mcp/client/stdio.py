import asyncio
from contextlib import asynccontextmanager
from .models import StdioServerParameters

@asynccontextmanager
async def stdio_client(params: StdioServerParameters):
    process = await asyncio.create_subprocess_exec(
        params.command,
        *params.args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        env=params.env
    )
    
    try:
        yield (process.stdout, process.stdin)
    finally:
        process.terminate()
        await process.wait()