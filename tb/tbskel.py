"""soc-linux 的端到端测试台。

验的是整条链路：外部总线 -> 交换网 -> 内存，核取指、执行、访存，再穿过同一张
地址图去够别的设备。装配、仲裁、译码、核，任何一处错都在这里现形。

流程：拉住 halt，从外部总线把程序写进内存，放开 halt，等它跑完，再从外部总线
把结果读回来对。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from rasm import assemble  # noqa: E402

RES = 0x7F0    # 结果放在内存的这个偏移起（12 位有符号立即数放得下）

SRC = [
    "  lui  a0, 0x80000",        # a0 = 0x8000_0000，内存基址
    "  addi t0, zero, 42",
    "  sw   t0, 0x7F0(a0)",
    "  csrrs t1, 0xF14, zero",   # mhartid，测试台喂 1 进去
    "  sw   t1, 0x7F4(a0)",
    "  lui  a1, 0x02004",        # a1 = 0x0200_4000，clint 的 mtimecmp
    "  addi t2, zero, 0x123",
    "  sw   t2, 0(a1)",
    "  lw   t3, 0(a1)",          # 穿过同一张地址图去够另一个设备
    "  sw   t3, 0x7F8(a0)",
    "done:",
    "  jal  zero, done",
]
EXPECT = [(RES, 42), (RES + 4, 1), (RES + 8, 0x123)]

prog = assemble(SRC)
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out.mkdir(parents=True, exist_ok=True)

rom = "\n".join(f"      {i}: return 32'h{w:08X};" for i, w in enumerate(prog))
chk = "\n".join(f"      {i}: return tuple2(32'h{0x80000000 + a:08X}, "
                f"32'h{v:08X});" for i, (a, v) in enumerate(EXPECT))

(out / "SocProg.bsv").write_text(f"""package SocProg;

// 由 tb/mksoctb.py 生成，勿手改。

Integer progLen = {len(prog)};
Integer chkLen  = {len(EXPECT)};

function Bit#(32) progWord(Bit#(32) i);
  case (i)
{rom}
    default: return 32'h00000013;
  endcase
endfunction

function Tuple2#(Bit#(32), Bit#(32)) checkAt(Bit#(32) i);
  case (i)
{chk}
    default: return tuple2(0, 0);
  endcase
endfunction

endpackage
""", encoding="utf-8")

(out / "SocTb.bsv").write_text('''package SocTb;

import Apb4::*;
import Hart::*;
import Uart::*;
import Aclint::*;
import Plic::*;
import SocLinuxPkg::*;
import SocProg::*;

// 端到端：装程序 -> 放核 -> 读结果。整条链路上任何一处错都在这里现形。

typedef enum { Load, Run, Read, Done } Phase deriving (Bits, Eq);

(* synthesize *)
module mkSocTb(Empty);
  SocLinuxIfc soc <- mkSocLinux;

  Reg#(Phase)    ph   <- mkReg(Load);
  Reg#(Bit#(32)) idx  <- mkReg(0);
  Reg#(Bit#(2))  st   <- mkReg(0);   // APB4 的两拍：0 建立，1 访问
  Reg#(Bit#(32)) wait_ <- mkReg(0);
  Reg#(Bool)     bad  <- mkReg(False);

  Bool loading = ph == Load;
  Bool reading = ph == Read;
  Bool active  = loading || reading;

  Bit#(32) addr = loading ? (32'h8000_0000 + (idx << 2))
                          : tpl_1(checkAt(idx));
  Bit#(32) wdat = progWord(idx);

  rule drive;
    // 装程序与读结果都走外部总线；核在装的时候被 halt 拉住
    soc.bus.req(addr, 3'b000, active, active && st == 1,
                loading, wdat, 4'hF);
    soc.cpu_pins.halt(ph == Load);
    soc.cpu_pins.hartid(1);
    soc.cpu_pins.irq(False, False, False);
    soc.clint_pins.tick(0);
    soc.plic0_pins.src(0);
    soc.uart0_pins.rxd(1);
    soc.uart0_pins.cts(1);
  endrule

  rule step;
    case (ph)
      Load: begin
        if (st == 0) st <= 1;
        else if (soc.bus.pready) begin
          st <= 0;
          if (idx + 1 == fromInteger(progLen)) begin
            ph <= Run; idx <= 0; wait_ <= 0;
          end else idx <= idx + 1;
        end
      end
      Run: begin
        // 放开核，给它跑完的时间
        if (wait_ > 4000) begin ph <= Read; idx <= 0; st <= 0; end
        else wait_ <= wait_ + 1;
      end
      Read: begin
        if (st == 0) st <= 1;
        else if (soc.bus.pready) begin
          st <= 0;
          Bit#(32) want = tpl_2(checkAt(idx));
          if (soc.bus.prdata != want) begin
            $display("FAIL check %0d at %08h: got %08h want %08h",
                     idx, addr, soc.bus.prdata, want);
            bad <= True;
          end
          if (idx + 1 == fromInteger(chkLen)) ph <= Done;
          else idx <= idx + 1;
        end
      end
      Done: begin
        if (bad) $display("FAILED");
        else $display("PASS all %0d end to end checks", chkLen);
        $finish(bad ? 1 : 0);
      end
    endcase
  endrule
endmodule

endpackage
''', encoding="utf-8")
print(f"  程序 {len(prog)} 条，端到端检查 {len(EXPECT)} 项")
