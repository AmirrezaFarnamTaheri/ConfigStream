import logging
import ssl
from ssl import SSLError

import httpx
from app.config import PANEL_CUSTOM_NODES, PANEL_NODE_RESET
from app.models.pg_node import PGNode
from app.models.panel import Panel
from app.notification.telegram import send_notification
from app.service.check_service import CheckService
from app.utils.panel.pasarguard_panel import get_token
import asyncio
from app.notification import reload_ad

from app.utils.panel.pasarguard_panel import get_pg_nodes
from app.utils.parser import parse_log_to_user

logger = logging.getLogger(__name__)

TASKS = []

task_node_mapping = {}


class PGNodeService:

    def __init__(self, check_service: CheckService):
        self._check_service = check_service

    async def get_nodes_logs(self, panel_data: Panel, node: PGNode) -> None:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        for scheme in ["https", "http"]:
            url = f"{scheme}://{panel_data.domain}/api/node/{node.id}/logs"
            while True:
                try:
                    get_panel_token = await get_token(panel_data)
                    if isinstance(get_panel_token, ValueError):
                        raise get_panel_token
                    
                    headers = {
                        "Authorization": f"Bearer {get_panel_token.token}",
                        "Accept": "text/event-stream",
                    }

                    async with httpx.AsyncClient(verify=ssl_context) as client:
                        log_message = f"Establishing SSE connection for pg node {node.id} ({node.name})"
                        logger.info(log_message)
                        await send_notification(log_message)

                        async with client.stream("GET", url, headers=headers, timeout=None) as response:
                            if response.status_code != 200:
                                logger.error(f"Failed to connect: {response.status_code}")
                                await asyncio.sleep(10)
                                continue

                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                
                                clean_log = line.replace("data: ", "").strip()
                                
                                log = parse_log_to_user(clean_log)
                                if log:
                                    log.node = node.name
                                    asyncio.create_task(self._check_service.check(log))

                except SSLError as e:
                    break

                except (httpx.ConnectError, httpx.RemoteProtocolError) as error:
                    log_message = (
                        f"Failed to connect to this pg node [pg node id: {node.id}]"
                        + f" [pg node name: {node.name}]"
                        + f" [pg node ip: {node.address}] [pg node message: {node.message}]"
                        + f" [Error Message: {error}] trying to connect 10 second later!"
                    )
                    logger.error(log_message)
                    await send_notification(log_message)
                    await asyncio.sleep(10)
                    continue
                    
                except Exception as error:
                    logger.exception(f"Unexpected error in log stream for node {node.id}: {error}")
                    await asyncio.sleep(10)
                    continue

    async def handle_cancel_all(self, tasks: list[asyncio.Task], panel_data: PGNode) -> None:
        async with asyncio.TaskGroup() as tg:
            while True:
                await asyncio.sleep(PANEL_NODE_RESET)
                reload_ad()
                for task in tasks:
                    logger.info(f"Cancelling {task.get_name()}...")
                    task.cancel()
                    tasks.remove(task)

                pg_nodes = await get_pg_nodes(panel_data)
                if PANEL_CUSTOM_NODES:
                    pg_nodes = [
                        m for m in pg_nodes if m.name in PANEL_CUSTOM_NODES]
                for pg_node in pg_nodes:
                    asyncio.create_task(
                        self.create_node_task(panel_data, tg, pg_node))
                    await asyncio.sleep(3)

    async def create_node_task(self,
                               panel_data: Panel, tg: asyncio.TaskGroup, node: PGNode
                               ) -> None:
        task = tg.create_task(
            self.get_nodes_logs(panel_data, node), name=f"Task-{node.id}-{node.name}"
        )
        TASKS.append(task)
        task_node_mapping[task] = node
