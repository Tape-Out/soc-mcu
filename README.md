# soc-mcu

Microcontroller reference SoC: one core, on-chip memory, the common peripherals. No MMU; the Linux target on this line is no-MMU Linux. The MMU line is [`soc-mpu`](https://github.com/Tape-Out/soc-mpu).

![maturity](https://img.shields.io/badge/maturity-planned-lightgrey) ![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0%20OR%20MulanPSL--2.0-blue)

Part of the [Tape-Out](https://github.com/Tape-Out) IP library: Bluespec IP over the
bus-neutral contracts in [`hwcore`](https://github.com/Tape-Out/hwcore), assembled by
[`xirang`](https://github.com/Tape-Out/xirang). Maturity runs `planned` -> `simulated` ->
`fpga-proven` -> `asic-ready` -> `silicon-proven`.

## Status

Assembled and tested end to end in CI; the badge stays at `planned` while the assembler is being reworked.

| Part | Repository | Configuration |
|:--:|:--:|:--:|
| core | [`rvcore`](https://github.com/Tape-Out/rvcore) | RV32IM, machine mode only, no MMU |
| memory | [`sram`](https://github.com/Tape-Out/sram) | 256 words (1 KiB) at `0x8000_0000` |
| timer and software interrupt | [`aclint`](https://github.com/Tape-Out/aclint) | one hart |
| peripherals | `gpio` ×2 · `uart` ×2 · `timer` · `pwm` · `wdt` · `spi` · `i2c` · `rtc` · `pinmux` | at `0x1000_xxxx` |

The core's two ports and an external APB4 port share one switch, round-robin among the on-chip managers. There is no interrupt controller: only the CLINT's software and timer interrupts reach the core, and the peripherals' interrupt lines come out as the top-level `irqs` vector.

## License

任选其一：

- [MIT](LICENSE-MIT)
- [Apache 2.0](LICENSE-APACHE)
- [木兰宽松许可证 第2版](LICENSE-MULAN)

`SPDX-License-Identifier: MIT OR Apache-2.0 OR MulanPSL-2.0`

除非另行说明，你提交的贡献按上述三者同时授权，不附加其他条件。
