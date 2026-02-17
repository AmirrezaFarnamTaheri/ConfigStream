file_path = "src/configstream/tools/vwarp.py"
with open(file_path, "r") as f:
    content = f.read()

# Update start_tunnel signature
# Original:
#     async def start_tunnel(
#         self, bind_addr: str = VWARP_BIND_ADDRESS, port: int = VWARP_SOCKS5_PORT
#     ) -> bool:

# Replacement:
#     async def start_tunnel(
#         self,
#         bind_addr: str = VWARP_BIND_ADDRESS,
#         port: int = VWARP_SOCKS5_PORT,
#         config_override: Optional[Dict[str, Any]] = None,
#     ) -> bool:

old_sig = """    async def start_tunnel(
        self, bind_addr: str = VWARP_BIND_ADDRESS, port: int = VWARP_SOCKS5_PORT
    ) -> bool:"""

new_sig = """    async def start_tunnel(
        self,
        bind_addr: str = VWARP_BIND_ADDRESS,
        port: int = VWARP_SOCKS5_PORT,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> bool:"""

content = content.replace(old_sig, new_sig)

# Update internal call to attempt (or _start_tunnel_once)
# We need to make sure `attempt` function uses `config_override`.
# The `attempt` function inside `start_tunnel` takes an override argument.
# But the initial call inside `start_tunnel` needs to pass the outer `config_override`.

# Let's inspect the body of start_tunnel first.
# It seems complex with retries.
# I should read more of the body.
