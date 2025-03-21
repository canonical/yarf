from pathlib import Path
from typing import Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

YARF_PATH = Path(__file__).parent
INPUT_DIR = YARF_PATH / "data" / "wayland"
OUTPUT_DIR = YARF_PATH / "yarf" / "lib" / "wayland" / "protocols"


def generate_protocol(name: str, imports: Dict[str, str]) -> Dict[str, str]:
    import pywayland
    import pywayland.scanner

    proto = pywayland.scanner.Protocol.parse_file(
        str(INPUT_DIR / f"{name}.xml")
    )
    proto_imports = {iface.name: proto.name for iface in proto.interface}
    proto.output(str(OUTPUT_DIR), dict(proto_imports, **imports))
    return proto_imports


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data) -> None:
        core_imports = generate_protocol("wayland", {})
        generate_protocol("virtual-keyboard-unstable-v1", core_imports)
        generate_protocol("wlr-screencopy-unstable-v1", core_imports)
        generate_protocol("wlr-virtual-pointer-unstable-v1", core_imports)
        generate_protocol("xdg-output-unstable-v1", core_imports)
