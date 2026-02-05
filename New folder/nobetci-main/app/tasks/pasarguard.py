import asyncio
from app.config import PANEL_ADDRESS, PANEL_CUSTOM_NODES, PANEL_PASSWORD, PANEL_USERNAME
from app.models.panel import Panel
from app.service.check_service import CheckService
from app.service.pg_node_service import TASKS, PGNodeService
from app.tasks.nodes import nodes_startup
from app import user_limit_db, storage
from app.db import node_db
from app.utils.panel.pasarguard_panel import get_pg_nodes


async def start_pg_node_tasks():
    await nodes_startup(node_db.get_all(True))

    paneltype = Panel(
        username=PANEL_USERNAME,
        password=PANEL_PASSWORD,
        domain=PANEL_ADDRESS,
    )

    node_service = PGNodeService(CheckService(
        storage, user_limit_db))

    pg_nodes = await get_pg_nodes(paneltype)

    if PANEL_CUSTOM_NODES:
        pg_nodes = [m for m in pg_nodes if m.name in PANEL_CUSTOM_NODES]

    async with asyncio.TaskGroup() as tg:
        for pg_node in pg_nodes:
            await node_service.create_node_task(paneltype, tg, pg_node)
        tg.create_task(
            node_service.handle_cancel_all(TASKS, paneltype),
            name="cancel_all",
        )
