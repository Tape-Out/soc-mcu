"""soc-mcu 的端到端测试台：借 soc-linux 那份的骨架，只换名字与要驱动的引脚。

装程序 -> 放核 -> 读结果，跟 soc-linux 那份是同一条链路；差别在外设多，
而它们的输入引脚都是 always_enabled，**每拍必须有值**。空着不是「不连」，
bsc 会判条件恒假（G0066）并把要驱动的方法逐个列出来——照着补即可。
"""
import json
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
src = (here / "tbskel.py").read_text(encoding="utf-8")

IMPORTS = "\n".join([
    "import GpioGen::*;",
    "import Timer::*;",
    "import Pwm::*;",
    "import Wdt::*;",
    "import Spi::*;",
    "import I2c::*;",
    "import Pinmux::*;",
])

PINS = "\n".join([
    "    // 这些外设测试台用不上，但引脚都是 always_enabled，每拍得有个值",
    "    soc.uart1_pins.rxd(1);",
    "    soc.uart1_pins.cts(1);",
    "    soc.gpioa_pins.pin_in(0);",
    "    soc.gpiob_pins.pin_in(0);",
    "    soc.timer0_pins.capt(0);",
    "    soc.spi0_pins.io_i(0);",
    "    soc.i2c0_pins.scl_in(1);",
    "    soc.i2c0_pins.sda_in(1);",
    "    soc.pinmux0_pins_if.func_o(0);",
    "    soc.pinmux0_pins_if.func_oe(0);",
    "    soc.pinmux0_pins_if.pad_i(0);",
    "",
])

knobs = json.loads(sys.argv[2])["knobs"] if len(sys.argv) > 2 else {}


def swap(old: str, new: str) -> None:
    # 骨架改了而这里没跟上，替换就静默落空，生成的还是原样那份
    global src
    if src.count(old) != 1:
        raise SystemExit(f"骨架里找不到这一段：{old.strip()[:40]}")
    src = src.replace(old, new)


if knobs.get("cpu.mul", True):
    # 乘法关着时这是非法指令，那时 mtvec 还没设，核会跑飞
    swap('    "  sw   t3, 0x7F8(a0)",\n',
         '    "  sw   t3, 0x7F8(a0)",\n'
         '    "  addi t4, zero, 7",\n'
         '    "  addi t5, zero, 6",\n'
         '    "  mul  t6, t4, t5",\n'
         '    "  sw   t6, 0x7EC(a0)",\n')
    swap("EXPECT = [(RES, 42),", "EXPECT = [(RES - 4, 42), (RES, 42),")

src = src.replace("soc-linux 的端到端测试台", "soc-mcu 的端到端测试台")
src = src.replace("import SocLinuxPkg::*;", "import SocMcuPkg::*;")
src = src.replace("SocLinuxIfc soc <- mkSocLinux;", "SocMcuIfc soc <- mkSocMcu;")
src = src.replace("import Plic::*;", IMPORTS)
src = src.replace("    soc.plic0_pins.src(0);\n", PINS)
src = src.replace('(out / "SocTb.bsv")', '(out / "McuTb.bsv")')
src = src.replace("package SocTb;", "package McuTb;")
src = src.replace("module mkSocTb(Empty);", "module mkMcuTb(Empty);")
g = {"__name__": "__main__", "__file__": str(here / "tbskel.py"), "sys": sys}
exec(compile(src, "mkmcutb", "exec"), g)
