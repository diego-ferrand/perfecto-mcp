import traceback
from typing import Optional, Any, Dict

import httpx
from mcp.server.fastmcp import Context
from pydantic import Field

from config.perfecto import TOOLS_PREFIX, SUPPORT_MESSAGE, get_real_devices_extended_commands_help_url, \
    get_real_devices_extended_command_base_help_url
from config.token import PerfectoToken
from formatters.help import format_list_real_devices_extended_commands_info, \
    format_read_real_devices_extended_command_info
from models.manager import Manager
from models.result import BaseResult
from tools.utils import http_request


class HelpManager(Manager):
    def __init__(self, token: Optional[PerfectoToken], ctx: Context):
        super().__init__(token, ctx)

    @staticmethod
    async def list_real_devices_extended_commands() -> BaseResult:
        real_devices_extended_commands_help_url = get_real_devices_extended_commands_help_url()
        return await http_request("GET", endpoint=real_devices_extended_commands_help_url,
                                  result_formatter=format_list_real_devices_extended_commands_info)

    @staticmethod
    async def read_real_devices_extended_command_info(command_id: str) -> BaseResult:
        real_devices_extended_command_help_url = get_real_devices_extended_command_base_help_url()
        real_devices_extended_command_help_url = f"{real_devices_extended_command_help_url}{command_id}.htm"
        return await http_request("GET", endpoint=real_devices_extended_command_help_url,
                                  result_formatter=format_read_real_devices_extended_command_info,
                                  result_formatter_params={"base_url": real_devices_extended_command_help_url})


def register(mcp, token: Optional[PerfectoToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_help",
        description="""
Operations on documentation and help information.
Actions:
- list_real_devices_extended_commands: Perfecto provides support for extended RemoteWebDriver commands. You can use these commands as extensions to the default SDK. Perfecto extensions are also known as function references (FR).
- read_real_devices_extended_command_info: Read the detailed command information.
    args(dict): Dictionary with the following required parameters:
        command_id (str): The command id.
Hints:
- Always generates the url attributes as a link in markdown format (like command_url).
"""
    )
    async def help_main(
            action: str = Field(description="The action id to execute"),
            args: Dict[str, Any] = Field(description="Dictionary with parameters"),
            ctx: Context = Field(description="Context object providing access to MCP capabilities")
    ) -> BaseResult:

        help_manager = HelpManager(token, ctx)
        try:
            match action:
                case "list_real_devices_extended_commands":
                    return await help_manager.list_real_devices_extended_commands()
                case "read_real_devices_extended_command_info":
                    return await help_manager.read_real_devices_extended_command_info(args["command_id"])
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in help manager tool"
                    )
        except httpx.HTTPStatusError:
            return BaseResult(
                error=f"Error: {traceback.format_exc()}"
            )
        except Exception:
            return BaseResult(
                error=f"Error: {traceback.format_exc()}\n{SUPPORT_MESSAGE}"
            )
