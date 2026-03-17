"""WASM loading, parsing, and reference execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
import shutil
import subprocess
import tempfile


MAGIC = b"\x00asm"
VERSION = b"\x01\x00\x00\x00"
WAT2WASM = shutil.which("wat2wasm")
CLANG = shutil.which("clang")


class SectionId(IntEnum):
    CUSTOM = 0
    TYPE = 1
    IMPORT = 2
    FUNCTION = 3
    TABLE = 4
    MEMORY = 5
    GLOBAL = 6
    EXPORT = 7
    START = 8
    ELEMENT = 9
    CODE = 10
    DATA = 11


class ValueType(IntEnum):
    I32 = 0x7F


class WasmOpcode(IntEnum):
    BLOCK = 0x02
    LOOP = 0x03
    IF = 0x04
    ELSE = 0x05
    END = 0x0B
    BR = 0x0C
    BR_IF = 0x0D
    RETURN = 0x0F
    DROP = 0x1A
    LOCAL_GET = 0x20
    LOCAL_SET = 0x21
    LOCAL_TEE = 0x22
    I32_LOAD = 0x28
    I32_STORE = 0x36
    I32_CONST = 0x41
    I32_LT_S = 0x48
    I32_GT_S = 0x4A
    I32_LE_S = 0x4C
    I32_EQZ = 0x45
    I32_ADD = 0x6A
    I32_SUB = 0x6B
    I32_MUL = 0x6C


MNEMONICS = {
    WasmOpcode.BLOCK: "block",
    WasmOpcode.LOOP: "loop",
    WasmOpcode.IF: "if",
    WasmOpcode.ELSE: "else",
    WasmOpcode.END: "end",
    WasmOpcode.BR: "br",
    WasmOpcode.BR_IF: "br_if",
    WasmOpcode.RETURN: "return",
    WasmOpcode.DROP: "drop",
    WasmOpcode.LOCAL_GET: "local.get",
    WasmOpcode.LOCAL_SET: "local.set",
    WasmOpcode.LOCAL_TEE: "local.tee",
    WasmOpcode.I32_LOAD: "i32.load",
    WasmOpcode.I32_STORE: "i32.store",
    WasmOpcode.I32_CONST: "i32.const",
    WasmOpcode.I32_LT_S: "i32.lt_s",
    WasmOpcode.I32_GT_S: "i32.gt_s",
    WasmOpcode.I32_LE_S: "i32.le_s",
    WasmOpcode.I32_EQZ: "i32.eqz",
    WasmOpcode.I32_ADD: "i32.add",
    WasmOpcode.I32_SUB: "i32.sub",
    WasmOpcode.I32_MUL: "i32.mul",
}


def mask_u32(value: int) -> int:
    return value & 0xFFFFFFFF


def to_signed_i32(value: int) -> int:
    masked = mask_u32(value)
    return masked if masked < 0x80000000 else masked - 0x100000000


@dataclass(slots=True)
class FunctionType:
    params: list[ValueType]
    results: list[ValueType]


@dataclass(slots=True)
class MemoryType:
    min_pages: int
    max_pages: int | None = None


@dataclass(slots=True)
class WasmInstruction:
    opcode: WasmOpcode
    immediate: int | None = None
    branch_target: int | None = None
    end_target: int | None = None
    false_target: int | None = None
    memory_align: int | None = None
    memory_offset: int | None = None

    @property
    def mnemonic(self) -> str:
        return MNEMONICS[self.opcode]

    def __str__(self) -> str:
        if self.opcode in {WasmOpcode.I32_LOAD, WasmOpcode.I32_STORE}:
            align = self.memory_align or 0
            offset = self.memory_offset or 0
            return f"{self.mnemonic} align={align} offset={offset}"
        if self.immediate is None:
            return self.mnemonic
        if self.branch_target is not None and self.opcode in {WasmOpcode.BR, WasmOpcode.BR_IF}:
            return f"{self.mnemonic} {self.immediate} -> {self.branch_target}"
        return f"{self.mnemonic} {self.immediate}"


@dataclass(slots=True)
class WasmFunction:
    type_: FunctionType
    local_types: list[ValueType]
    instructions: list[WasmInstruction]
    body_bytes: bytes
    export_names: list[str] = field(default_factory=list)
    initial_memory_pages: int = 0
    initial_memory: dict[int, int] = field(default_factory=dict)

    @property
    def local_count(self) -> int:
        return len(self.type_.params) + len(self.local_types)

    @property
    def result_count(self) -> int:
        return len(self.type_.results)

    def token_stream(self) -> list[int]:
        return list(self.body_bytes)


@dataclass(slots=True)
class WasmModule:
    types: list[FunctionType]
    functions: list[WasmFunction]
    exports: dict[str, int]
    raw_bytes: bytes
    memory: MemoryType | None = None

    def exported_function(self, name: str = "main") -> WasmFunction:
        if name not in self.exports:
            raise KeyError(f"Unknown export: {name}")
        return self.functions[self.exports[name]]


@dataclass(slots=True)
class TraceEntry:
    step: int
    ip: int
    instruction: str
    value: int
    stack_delta: int
    stack_size: int
    branch_taken: bool


@dataclass(slots=True)
class ExecutionResult:
    results: list[int]
    trace: list[TraceEntry]
    locals_: list[int]


@dataclass(slots=True)
class ControlFrame:
    opcode: WasmOpcode
    start_index: int
    forward_fixups: list[int]
    else_index: int | None = None


class ByteReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def read_byte(self) -> int:
        if self.pos >= len(self.data):
            raise EOFError("Unexpected end of WASM data")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_bytes(self, size: int) -> bytes:
        end = self.pos + size
        if end > len(self.data):
            raise EOFError("Unexpected end of WASM data")
        value = self.data[self.pos:end]
        self.pos = end
        return value

    def read_u32(self) -> int:
        shift = 0
        value = 0
        while True:
            byte = self.read_byte()
            value |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                return value
            shift += 7
            if shift > 35:
                raise ValueError("Invalid unsigned LEB128")

    def read_i32(self) -> int:
        shift = 0
        value = 0
        byte = 0
        while True:
            byte = self.read_byte()
            value |= (byte & 0x7F) << shift
            shift += 7
            if byte & 0x80 == 0:
                break
            if shift > 35:
                raise ValueError("Invalid signed LEB128")
        if shift < 32 and byte & 0x40:
            value |= -1 << shift
        return value

    def read_name(self) -> str:
        return self.read_bytes(self.read_u32()).decode("utf-8")

    def read_block_type(self) -> int:
        first = self.read_byte()
        if first & 0x80 == 0:
            if first & 0x40:
                return first - 0x80
            return first

        shift = 7
        value = first & 0x7F
        byte = first
        while byte & 0x80:
            byte = self.read_byte()
            value |= (byte & 0x7F) << shift
            shift += 7
            if shift > 35:
                raise ValueError("Invalid block type encoding")
        if shift < 33 and byte & 0x40:
            value |= -1 << shift
        return value


def compile_wat(wat_source: str) -> bytes:
    if WAT2WASM is None:
        raise RuntimeError("wat2wasm is required but was not found in PATH")

    with tempfile.TemporaryDirectory() as tmpdir:
        wat_path = Path(tmpdir) / "module.wat"
        wasm_path = Path(tmpdir) / "module.wasm"
        wat_path.write_text(wat_source, encoding="utf-8")
        result = subprocess.run(
            [WAT2WASM, str(wat_path), "-o", str(wasm_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "wat2wasm failed")
        return wasm_path.read_bytes()


def compile_wat_module(wat_source: str) -> WasmModule:
    return parse_module(compile_wat(wat_source))


def compile_c(source: str, export_name: str, opt_level: str = "-O2") -> bytes:
    if CLANG is None:
        raise RuntimeError("clang is required but was not found in PATH")

    with tempfile.TemporaryDirectory() as tmpdir:
        c_path = Path(tmpdir) / "module.c"
        wasm_path = Path(tmpdir) / "module.wasm"
        c_path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [
                CLANG,
                "--target=wasm32",
                opt_level,
                "-nostdlib",
                "-Wl,--no-entry",
                f"-Wl,--export={export_name}",
                str(c_path),
                "-o",
                str(wasm_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "clang wasm compilation failed")
        return wasm_path.read_bytes()


def compile_c_module(source: str, export_name: str, opt_level: str = "-O2") -> WasmModule:
    return parse_module(compile_c(source, export_name=export_name, opt_level=opt_level))


def parse_module(raw_bytes: bytes) -> WasmModule:
    reader = ByteReader(raw_bytes)
    if reader.read_bytes(4) != MAGIC:
        raise ValueError("Invalid WASM magic")
    if reader.read_bytes(4) != VERSION:
        raise ValueError("Unsupported WASM version")

    types: list[FunctionType] = []
    function_type_indices: list[int] = []
    exports: dict[str, int] = {}
    code_bodies: list[tuple[list[ValueType], list[WasmInstruction], bytes]] = []
    memory: MemoryType | None = None
    initial_memory: dict[int, int] = {}

    while reader.remaining() > 0:
        section_id = SectionId(reader.read_byte())
        payload = reader.read_bytes(reader.read_u32())
        section_reader = ByteReader(payload)

        if section_id == SectionId.CUSTOM:
            continue
        if section_id == SectionId.IMPORT:
            raise NotImplementedError("Imported functions are not supported in this prototype")
        if section_id == SectionId.TYPE:
            types = _parse_type_section(section_reader)
            continue
        if section_id == SectionId.FUNCTION:
            function_type_indices = _parse_function_section(section_reader)
            continue
        if section_id == SectionId.MEMORY:
            memory = _parse_memory_section(section_reader)
            continue
        if section_id == SectionId.EXPORT:
            exports = _parse_export_section(section_reader)
            continue
        if section_id == SectionId.CODE:
            code_bodies = _parse_code_section(section_reader)
            continue
        if section_id == SectionId.DATA:
            initial_memory = _parse_data_section(section_reader)
            continue

    if len(function_type_indices) != len(code_bodies):
        raise ValueError("Function and code section lengths do not match")

    functions: list[WasmFunction] = []
    for index, type_index in enumerate(function_type_indices):
        if not 0 <= type_index < len(types):
            raise ValueError(f"Unknown type index: {type_index}")
        local_types, instructions, body_bytes = code_bodies[index]
        functions.append(
            WasmFunction(
                type_=types[type_index],
                local_types=local_types,
                instructions=instructions,
                body_bytes=body_bytes,
                initial_memory_pages=memory.min_pages if memory is not None else 0,
                initial_memory=dict(initial_memory),
            )
        )

    for export_name, func_index in exports.items():
        if 0 <= func_index < len(functions):
            functions[func_index].export_names.append(export_name)

    return WasmModule(types=types, functions=functions, exports=exports, raw_bytes=raw_bytes, memory=memory)


def _parse_type_section(reader: ByteReader) -> list[FunctionType]:
    count = reader.read_u32()
    types: list[FunctionType] = []
    for _ in range(count):
        if reader.read_byte() != 0x60:
            raise ValueError("Unsupported function type form")
        params = [ValueType(reader.read_byte()) for _ in range(reader.read_u32())]
        results = [ValueType(reader.read_byte()) for _ in range(reader.read_u32())]
        types.append(FunctionType(params=params, results=results))
    return types


def _parse_function_section(reader: ByteReader) -> list[int]:
    return [reader.read_u32() for _ in range(reader.read_u32())]


def _parse_limits(reader: ByteReader) -> tuple[int, int | None]:
    flags = reader.read_u32()
    minimum = reader.read_u32()
    maximum = reader.read_u32() if flags & 0x01 else None
    return minimum, maximum


def _parse_memory_section(reader: ByteReader) -> MemoryType:
    count = reader.read_u32()
    if count != 1:
        raise NotImplementedError("Only a single linear memory is supported")
    minimum, maximum = _parse_limits(reader)
    return MemoryType(min_pages=minimum, max_pages=maximum)


def _parse_export_section(reader: ByteReader) -> dict[str, int]:
    exports: dict[str, int] = {}
    for _ in range(reader.read_u32()):
        name = reader.read_name()
        kind = reader.read_byte()
        index = reader.read_u32()
        if kind == 0:
            exports[name] = index
    return exports


def _read_const_i32_expr(reader: ByteReader) -> int:
    opcode = WasmOpcode(reader.read_byte())
    if opcode != WasmOpcode.I32_CONST:
        raise NotImplementedError("Only i32.const data offsets are supported")
    value = reader.read_i32()
    end_opcode = WasmOpcode(reader.read_byte())
    if end_opcode != WasmOpcode.END:
        raise ValueError("Malformed const expression")
    return value


def _parse_data_section(reader: ByteReader) -> dict[int, int]:
    memory: dict[int, int] = {}
    for _ in range(reader.read_u32()):
        flags = reader.read_u32()
        if flags == 0:
            offset = _read_const_i32_expr(reader)
        elif flags == 2:
            _ = reader.read_u32()
            offset = _read_const_i32_expr(reader)
        else:
            raise NotImplementedError("Passive data segments are not supported")
        data = reader.read_bytes(reader.read_u32())
        for index, byte in enumerate(data):
            memory[offset + index] = byte
    return memory


def _parse_code_section(reader: ByteReader) -> list[tuple[list[ValueType], list[WasmInstruction], bytes]]:
    functions: list[tuple[list[ValueType], list[WasmInstruction], bytes]] = []
    for _ in range(reader.read_u32()):
        body_bytes = reader.read_bytes(reader.read_u32())
        body_reader = ByteReader(body_bytes)
        local_types: list[ValueType] = []
        for _ in range(body_reader.read_u32()):
            repeat_count = body_reader.read_u32()
            value_type = ValueType(body_reader.read_byte())
            local_types.extend([value_type] * repeat_count)
        instructions = _parse_instructions(body_reader)
        if body_reader.remaining() != 0:
            raise ValueError("Unexpected bytes after function body")
        functions.append((local_types, instructions, body_bytes))
    return functions


def _parse_instructions(reader: ByteReader) -> list[WasmInstruction]:
    instructions: list[WasmInstruction] = []
    frames: list[ControlFrame] = []

    while True:
        opcode = WasmOpcode(reader.read_byte())

        if opcode in {WasmOpcode.BLOCK, WasmOpcode.LOOP, WasmOpcode.IF}:
            block_type = reader.read_block_type()
            instructions.append(WasmInstruction(opcode=opcode, immediate=block_type))
            frames.append(ControlFrame(opcode=opcode, start_index=len(instructions) - 1, forward_fixups=[]))
            continue

        if opcode == WasmOpcode.ELSE:
            if not frames or frames[-1].opcode != WasmOpcode.IF:
                raise ValueError("ELSE without matching IF")
            else_index = len(instructions)
            instructions.append(WasmInstruction(opcode=opcode))
            frame = frames[-1]
            frame.else_index = else_index
            instructions[frame.start_index].false_target = else_index + 1
            continue

        if opcode == WasmOpcode.END:
            end_index = len(instructions)
            instructions.append(WasmInstruction(opcode=opcode))
            if frames:
                frame = frames.pop()
                instructions[frame.start_index].end_target = end_index + 1
                if frame.opcode == WasmOpcode.IF and instructions[frame.start_index].false_target is None:
                    instructions[frame.start_index].false_target = end_index + 1
                if frame.else_index is not None:
                    instructions[frame.else_index].end_target = end_index + 1
                for fixup_index in frame.forward_fixups:
                    instructions[fixup_index].branch_target = end_index + 1
                continue
            break

        if opcode in {WasmOpcode.BR, WasmOpcode.BR_IF}:
            depth = reader.read_u32()
            instruction = WasmInstruction(opcode=opcode, immediate=depth)
            instructions.append(instruction)
            if depth >= len(frames):
                raise NotImplementedError("Branches to the implicit function block are not supported")
            target_frame = frames[-1 - depth]
            if target_frame.opcode == WasmOpcode.LOOP:
                instruction.branch_target = target_frame.start_index + 1
            else:
                target_frame.forward_fixups.append(len(instructions) - 1)
            continue

        if opcode == WasmOpcode.I32_CONST:
            instructions.append(WasmInstruction(opcode=opcode, immediate=reader.read_i32()))
            continue

        if opcode in {WasmOpcode.I32_LOAD, WasmOpcode.I32_STORE}:
            align = reader.read_u32()
            offset = reader.read_u32()
            instructions.append(WasmInstruction(opcode=opcode, memory_align=align, memory_offset=offset))
            continue

        if opcode in {WasmOpcode.LOCAL_GET, WasmOpcode.LOCAL_SET, WasmOpcode.LOCAL_TEE}:
            instructions.append(WasmInstruction(opcode=opcode, immediate=reader.read_u32()))
            continue

        if opcode in {
            WasmOpcode.I32_LT_S,
            WasmOpcode.I32_GT_S,
            WasmOpcode.I32_LE_S,
            WasmOpcode.I32_EQZ,
            WasmOpcode.I32_ADD,
            WasmOpcode.I32_SUB,
            WasmOpcode.I32_MUL,
            WasmOpcode.RETURN,
            WasmOpcode.DROP,
        }:
            instructions.append(WasmInstruction(opcode=opcode))
            continue

        raise NotImplementedError(f"Unsupported opcode: 0x{int(opcode):02x}")

    return instructions


class ReferenceWasmExecutor:
    """Runs a parsed WASM function with ordinary mutable state."""

    def __init__(self, function: WasmFunction) -> None:
        self.function = function
        self.locals = [0] * function.local_count
        self.stack: list[int] = []
        self.ip = 0
        self.step = 0
        self.trace: list[TraceEntry] = []
        self.memory: dict[int, int] = dict(function.initial_memory)

    def _push(self, value: int) -> None:
        self.stack.append(mask_u32(value))

    def _pop(self) -> int:
        return self.stack.pop() if self.stack else 0

    def _record(self, ip: int, instruction: WasmInstruction, value: int, stack_delta: int, branch_taken: bool) -> None:
        self.trace.append(
            TraceEntry(
                step=self.step,
                ip=ip,
                instruction=str(instruction),
                value=mask_u32(value),
                stack_delta=stack_delta,
                stack_size=len(self.stack),
                branch_taken=branch_taken,
            )
        )
        self.step += 1

    def _collect_results(self) -> list[int]:
        if self.function.result_count == 0:
            return []
        return [mask_u32(value) for value in self.stack[-self.function.result_count:]]

    def _check_memory_bounds(self, address: int, size: int) -> None:
        if address < 0:
            raise ValueError("Negative memory access")
        limit = self.function.initial_memory_pages * 65536
        if address + size > limit:
            raise ValueError("Out-of-bounds memory access")

    def _load_i32(self, address: int) -> int:
        self._check_memory_bounds(address, 4)
        value = 0
        for offset in range(4):
            value |= self.memory.get(address + offset, 0) << (offset * 8)
        return mask_u32(value)

    def _store_i32(self, address: int, value: int) -> None:
        self._check_memory_bounds(address, 4)
        masked = mask_u32(value)
        for offset in range(4):
            self.memory[address + offset] = (masked >> (offset * 8)) & 0xFF

    def run(self, max_steps: int = 200_000) -> ExecutionResult:
        while 0 <= self.ip < len(self.function.instructions) and self.step < max_steps:
            instruction = self.function.instructions[self.ip]
            ip_before = self.ip
            branch_taken = False
            stack_delta = 0
            value = 0

            if instruction.opcode in {WasmOpcode.BLOCK, WasmOpcode.LOOP, WasmOpcode.END}:
                self.ip += 1
            elif instruction.opcode == WasmOpcode.IF:
                cond = self._pop()
                stack_delta = -1
                if cond != 0:
                    self.ip += 1
                else:
                    self.ip = instruction.false_target or instruction.end_target or (self.ip + 1)
                    branch_taken = True
            elif instruction.opcode == WasmOpcode.ELSE:
                self.ip = instruction.end_target or (self.ip + 1)
                branch_taken = True
            elif instruction.opcode == WasmOpcode.I32_CONST:
                value = instruction.immediate or 0
                self._push(value)
                stack_delta = 1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.LOCAL_GET:
                index = instruction.immediate or 0
                value = self.locals[index]
                self._push(value)
                stack_delta = 1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.LOCAL_SET:
                index = instruction.immediate or 0
                value = self._pop()
                self.locals[index] = value
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.LOCAL_TEE:
                index = instruction.immediate or 0
                value = self._pop()
                self.locals[index] = value
                self._push(value)
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_LOAD:
                base = self._pop()
                address = base + (instruction.memory_offset or 0)
                value = self._load_i32(address)
                self._push(value)
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_STORE:
                value = self._pop()
                base = self._pop()
                address = base + (instruction.memory_offset or 0)
                self._store_i32(address, value)
                stack_delta = -2
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_LT_S:
                rhs = self._pop()
                lhs = self._pop()
                value = 1 if to_signed_i32(lhs) < to_signed_i32(rhs) else 0
                self._push(value)
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_GT_S:
                rhs = self._pop()
                lhs = self._pop()
                value = 1 if to_signed_i32(lhs) > to_signed_i32(rhs) else 0
                self._push(value)
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_LE_S:
                rhs = self._pop()
                lhs = self._pop()
                value = 1 if to_signed_i32(lhs) <= to_signed_i32(rhs) else 0
                self._push(value)
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_ADD:
                rhs = self._pop()
                lhs = self._pop()
                value = lhs + rhs
                self._push(value)
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_SUB:
                rhs = self._pop()
                lhs = self._pop()
                value = lhs - rhs
                self._push(value)
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_MUL:
                rhs = self._pop()
                lhs = self._pop()
                value = lhs * rhs
                self._push(value)
                stack_delta = -1
                self.ip += 1
            elif instruction.opcode == WasmOpcode.I32_EQZ:
                value = 1 if self._pop() == 0 else 0
                self._push(value)
                self.ip += 1
            elif instruction.opcode == WasmOpcode.BR:
                value = instruction.branch_target or 0
                self.ip = value
                branch_taken = True
            elif instruction.opcode == WasmOpcode.BR_IF:
                cond = self._pop()
                stack_delta = -1
                if cond != 0:
                    value = instruction.branch_target or 0
                    self.ip = value
                    branch_taken = True
                else:
                    self.ip += 1
            elif instruction.opcode == WasmOpcode.RETURN:
                self._record(ip_before, instruction, value, stack_delta, branch_taken)
                return ExecutionResult(results=self._collect_results(), trace=self.trace[:], locals_=self.locals[:])
            elif instruction.opcode == WasmOpcode.DROP:
                value = self._pop()
                stack_delta = -1
                self.ip += 1
            else:
                raise ValueError(f"Unsupported opcode: {instruction.opcode}")

            self._record(ip_before, instruction, value, stack_delta, branch_taken)

        return ExecutionResult(results=self._collect_results(), trace=self.trace[:], locals_=self.locals[:])
