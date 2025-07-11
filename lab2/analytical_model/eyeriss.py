import sys
from dataclasses import asdict, dataclass
from math import ceil, floor
from pathlib import Path

project_root = Path(__file__).parents[1]
sys.path.append(str(project_root))

from layer_info import Conv2DShapeParam, MaxPool2DShapeParam

# Memory
DATA_SIZE = 1  # Byte
PSUM_DATA_SIZE = 4  # Byte
BUS_BANDWIDTH = 4  # Byte

# Time
CLOCK_RATE = 200 * 1e6  # 200 MHz
TIME_UNIT = 1  # cycle
SPAD_ACCESS_TIME = 1 * TIME_UNIT
GLB_ACCESS_TIME = 2 * TIME_UNIT
DRAM_ACCESS_TIME = 5 * TIME_UNIT

# Energy
ENERGY_UNIT = 1e-6  # 1 pJ = 10^6 uJ
ENERGY_PER_MAC = 2 * ENERGY_UNIT
ENERGY_PER_GLB_ACCESS = 10 * ENERGY_UNIT
ENERGY_PER_DRAM_ACCESS = 200 * ENERGY_UNIT
POWER_UNIT = 1  # 1 uW
POWER_LEAKAGE = 50 * POWER_UNIT

######################################################################################################
# N: number of ifmaps/ofmaps
# M: number of filters
# H/W: ifmap height/width
# R/S: filter height/width
# E/F: ofmap height/width
# U: stride
#  ----------------------------------------------------------------------------------------------
# m: ofmap channels in global buffer
# n: number of ifmaps in a pass
# e: width of PE-set
# p: number of filters in a pass
# q: (ifmap or filter) channels in a pass
# r: number of PE sets for different (ifmap/filter) channels
# t: number of PE sets for different filters
#  ----------------------------------------------------------------------------------------------
#  Naming Convention
# *_per_pass: compute / storage size required per pass
# *_per_layer: compute / storage size required per layer
######################################################################################################


@dataclass
class EyerissHardwareParam:
    pe_array_h: int
    pe_array_w: int
    ifmap_spad_size: int
    filter_spad_size: int
    psum_spad_size: int
    glb_size: int
    bus_bw: int
    noc_bw: int


@dataclass
class EyerissMappingParam:
    m: int  # number of ofmap channels stored in global buffer
    n: int  # number of ofmaps/ifmaps used in a processing pass
    e: int  # width of the PE set (strip-mined if nessary)
    p: int  # number of filters processed by a PE set
    q: int  # number of ifmap/filter channels processed by a PE set
    r: int  # number of PE sets for different ifmap/filter channels
    t: int  # number of PE sets for different filters


AnalysisResult = dict[str, str | int | float]


class EyerissAnalyzer:
    cnt = 0

    def __init__(
        self,
        name: str | None = None,
        hardware_param: EyerissHardwareParam | None = None,
    ) -> None:
        self.name = name if name is not None else f"mapping_{EyerissAnalyzer.cnt}"
        self._hardware = hardware_param
        self._conv_shape = None
        self._maxpool_shape = None
        self._mapping = None
        EyerissAnalyzer.cnt += 1

    @property
    def hardware(self) -> EyerissHardwareParam:
        return self._hardware

    @hardware.setter
    def hardware(self, hardware_param: EyerissHardwareParam) -> None:
        assert isinstance(hardware_param, EyerissHardwareParam)
        self._hardware = hardware_param

    @property
    def conv_shape(self) -> Conv2DShapeParam:
        return self._conv_shape

    @conv_shape.setter
    def conv_shape(self, conv_param: Conv2DShapeParam) -> None:
        assert isinstance(conv_param, Conv2DShapeParam)
        self._conv_shape = conv_param

    @property
    def maxpool_shape(self) -> MaxPool2DShapeParam:
        return self._maxpool_shape

    @maxpool_shape.setter
    def maxpool_shape(self, maxpool_param: MaxPool2DShapeParam | None) -> None:
        assert isinstance(maxpool_param, (MaxPool2DShapeParam, type(None)))
        self._maxpool_shape = maxpool_param

    @property
    def mapping(self) -> EyerissMappingParam:
        return self._mapping

    @mapping.setter
    def mapping(self, mapping_param: EyerissMappingParam) -> None:
        self._mapping = mapping_param

    # Scratchpad Memory Usage
    def filter_used(self) -> int:
        return self.mapping.q * self.conv_shape.S * self.mapping.p

    def ifmap_used(self) -> int:
        return self.mapping.q * self.conv_shape.S

    def psum_used(self) -> int:
        return self.mapping.p

    @property
    def spad_size_legal(self) -> dict[str, bool]:
        return {
            "ifmap": self.ifmap_used() <= self.hardware.ifmap_spad_size,
            "filter": self.filter_used() <= self.hardware.filter_spad_size,
            "psum": self.psum_used() <= self.hardware.psum_spad_size,
        }

    # Global Buffer (GLB) Usage
    @property
    def glb_usage_per_pass(self) -> dict[str, int]:
        sizes: dict[str, int] = {}
        #! <<<========= Implement here =========>>>
        W = self.conv_shape.W
        R = self.conv_shape.R
        S = self.conv_shape.S
        F = self.conv_shape.F
        U = self.conv_shape.U
        n = self.mapping.n
        m = self.mapping.m
        qr = self.mapping.q * self.mapping.r
        pt = self.mapping.p * self.mapping.t
        e = self.mapping.e

        sizes["ifmap"] = n * qr * (U * (e - 1) + R) * W
        sizes["filter"] = pt * qr * R * S
        sizes["bias"] = pt * 4
        sizes["psum"] = n * m * e * F * 4

        sizes["total"] = (
            sizes["ifmap"]
            + sizes["filter"]
            + sizes["bias"]
            + sizes["psum"]
        )

        return sizes

    @property
    def glb_size_legal(self) -> bool:
        return self.glb_usage_per_pass["total"] <= self.hardware.glb_size

    # DRAM Accesses (DRAM-GLB data movement)
    @property
    def dram_access_per_layer(self) -> dict[str, int]:
        res: dict[str, int] = {}
        #! <<<========= Implement here =========>>>
        N = self.conv_shape.N
        W = self.conv_shape.W
        R = self.conv_shape.R
        S = self.conv_shape.S
        E = self.conv_shape.E
        F = self.conv_shape.F
        C = self.conv_shape.C
        M = self.conv_shape.M
        U = self.conv_shape.U
        n = self.mapping.n
        m = self.mapping.m
        qr = self.mapping.q * self.mapping.r
        e = self.mapping.e

        res["ifmap_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(C / qr)
            * n * qr * (U * (e - 1) + R) * W
        )

        res["filter_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(C / qr)
            * m * qr * R * S
        )
        res["bias_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * m * 4
        )

        if self.maxpool_shape is None:
            res["ofmap_write"] = (
                ceil(M / m)
                * ceil(E / e)
                * ceil(N / n)
                * n * m * e * F
            )
        else:
            kernel_size = self.maxpool_shape.kernel_size
            stride = self.maxpool_shape.stride
            res["ofmap_write"] = (
                ceil(M / m)
                * ceil(E / e)
                * ceil(N / n)
                * n * m * (floor((e - kernel_size) / stride) + 1) * (floor((F - kernel_size) / stride) + 1)
            )


        res["read"] = (
            res["ifmap_read"]
            + res["filter_read"]
            + res["bias_read"]
        )
        res["write"] = res["ofmap_write"]

        res["total"] = res["read"] + res["write"]

        return res

    # GLB Accesses (GLB-Spad data movement)
    @property
    def glb_access_per_layer(self) -> dict[str, int]:
        res: dict[str, int] = {}
        #! <<<========= Implement here =========>>>
        N = self.conv_shape.N
        W = self.conv_shape.W
        R = self.conv_shape.R
        S = self.conv_shape.S
        E = self.conv_shape.E
        F = self.conv_shape.F
        C = self.conv_shape.C
        M = self.conv_shape.M
        U = self.conv_shape.U
        n = self.mapping.n
        m = self.mapping.m
        qr = self.mapping.q * self.mapping.r
        pt = self.mapping.p * self.mapping.t
        e = self.mapping.e

        res["ifmap_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(C / qr)
            * ceil(m / pt)
            * n * qr * (U * (e - 1) + R) * W
        )

        res["filter_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(C / qr)
            * ceil(m / pt)
            * pt * qr * R * S
        )

        res["bias_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(m / pt)
            * pt * 4
        )

        res["psum_read"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(C / qr)
            * ceil(m / pt)
            * n * pt * e * F * 4
        )

        res["psum_write"] = (
            ceil(M / m)
            * ceil(E / e)
            * ceil(N / n)
            * ceil(C / qr)
            * ceil(m / pt)
            * n * pt * e * F * 4
        )

        if self.maxpool_shape is None:
            bias = (
                ceil(E / e)
                * ceil(N / n)
                * ceil(M / m)
                * m * e * F
            )
        else:
            kernel_size = self.maxpool_shape.kernel_size
            stride = self.maxpool_shape.stride
            bias = (
                ceil(E / e)
                * ceil(N / n)
                * ceil(M / m)
                * m * (floor((e - kernel_size) / stride) + 1) * (floor((F - kernel_size) / stride) + 1)
            )

        res["read"] = (
            res["ifmap_read"]
            + res["filter_read"]
            + res["bias_read"]
            + res["psum_read"]
        )
        res["write"] = res["psum_write"] + bias

        res["total"] = res["read"] + res["write"]

        return res

    @property
    def latency_per_layer(self) -> int:
        ofmap_size = (
            self.conv_shape.N
            * self.conv_shape.M
            * self.conv_shape.E
            * self.conv_shape.F
        )
        ppu_latency_per_elem = 1 if self.maxpool_shape is None else 5

        return (
            ceil(
                self.glb_access_per_layer["total"]
                * GLB_ACCESS_TIME
                / self.hardware.noc_bw
            )
            + ceil(
                self.dram_access_per_layer["total"]
                * DRAM_ACCESS_TIME
                / self.hardware.bus_bw
            )
            + ofmap_size * ppu_latency_per_elem
        )

    @property
    def macs_per_layer(self) -> int:
        return (
            self.conv_shape.N
            * self.conv_shape.M
            * self.conv_shape.E
            * self.conv_shape.F
            * self.conv_shape.C
            * self.conv_shape.R
            * self.conv_shape.S
        )

    @property
    def energy_per_layer(self) -> dict[str, float]:
        compute_energy = self.macs_per_layer * ENERGY_PER_MAC
        memory_energy = (
            self.glb_access_per_layer["total"] * ENERGY_PER_GLB_ACCESS
            + self.dram_access_per_layer["total"] * ENERGY_PER_DRAM_ACCESS
        )
        leakage_energy = POWER_LEAKAGE * self.latency_per_layer / CLOCK_RATE
        total_energy = compute_energy + memory_energy + leakage_energy
        return {
            "compute": compute_energy,
            "memory": memory_energy,
            "leakage": leakage_energy,
            "total": total_energy,
        }

    @property
    def power_per_layer(self) -> dict[str, float]:
        compute_power = (
            self.energy_per_layer["compute"] / self.latency_per_layer * CLOCK_RATE
        )
        memory_power = (
            self.energy_per_layer["memory"] / self.latency_per_layer * CLOCK_RATE
        )
        leakage_power = POWER_LEAKAGE
        total_power = compute_power + memory_power + leakage_power
        return {
            "compute": compute_power,
            "memory": memory_power,
            "leakage": leakage_power,
            "total": total_power,
        }

    @property
    def operational_intensity(self) -> float:
        return self.macs_per_layer / self.dram_access_per_layer["total"]

    @property
    def peak_performance(self) -> float:
        return self.hardware.pe_array_h * self.hardware.pe_array_w  # MACs per cycle

    @property
    def peak_bandwidth(self) -> float:
        return self.hardware.bus_bw  # bytes per cycle

    @property
    def bound_by(self) -> str:
        machine_blance_point = self.peak_performance / self.peak_bandwidth
        if self.operational_intensity > machine_blance_point:
            return "compute"
        elif self.operational_intensity < machine_blance_point:
            return "memory"
        else:
            return "balanced"

    @property
    def is_compute_bound(self) -> bool:
        return self.bound_by == "compute"

    @property
    def is_memory_bound(self) -> bool:
        return self.bound_by == "memory"

    @property
    def is_balanced(self) -> bool:
        return self.bound_by == "balanced"

    @property
    def summary(self) -> AnalysisResult:
        return {
            "layer": self.name,
            **asdict(self.hardware),
            **asdict(self.mapping),
            "glb_usage": self.glb_usage_per_pass["total"],  # bytes
            "glb_access": self.glb_access_per_layer["total"],  # bytes
            "dram_access": self.dram_access_per_layer["total"],  # bytes
            "macs": self.macs_per_layer,
            "latency": self.latency_per_layer,  # cycles
            "energy": self.energy_per_layer["total"],  # uJ
            "power": self.power_per_layer["total"],  # uW
                        # or any other metrics you want to include in the report
        }

if __name__ == "__main__":
    eyeriss = EyerissAnalyzer(
        name="Eyeriss",
        hardware_param=EyerissHardwareParam(
            pe_array_h=6,
            pe_array_w=8,
            ifmap_spad_size=12,
            filter_spad_size=48,
            psum_spad_size=16,
            glb_size=64 * 2**10,
            bus_bw=4,
            noc_bw=4,
        ),
    )
    eyeriss.mapping = EyerissMappingParam(m=16, n=1, e=8, p=4, q=4, r=1, t=2)

    conv_shapes = [
        Conv2DShapeParam(N=1, H=32, W=32, R=3, S=3, E=32, F=32, C=3, M=64, U=1),
        Conv2DShapeParam(N=1, H=16, W=16, R=3, S=3, E=16, F=16, C=64, M=192, U=1),
        Conv2DShapeParam(N=1, H=8, W=8, R=3, S=3, E=8, F=8, C=192, M=384, U=1),
        Conv2DShapeParam(N=1, H=8, W=8, R=3, S=3, E=8, F=8, C=384, M=256, U=1),
        Conv2DShapeParam(N=1, H=8, W=8, R=3, S=3, E=8, F=8, C=256, M=256, U=1),
    ]
    maxpool_shapes = [
        MaxPool2DShapeParam(N=1, kernel_size=2, stride=2),
        MaxPool2DShapeParam(N=1, kernel_size=2, stride=2),
        None,
        None,
        MaxPool2DShapeParam(N=1, kernel_size=2, stride=2),
    ]

    for i in range(len(conv_shapes)):
        eyeriss.conv_shape = conv_shapes[i]
        eyeriss.maxpool_shape = maxpool_shapes[i]
        print(f'GLB usage: {eyeriss.glb_usage_per_pass["total"]} bytes')
        print(f'GLB reads: {eyeriss.glb_access_per_layer["read"]} bytes')
        print(f'GLB write: {eyeriss.glb_access_per_layer["write"]} bytes')
        print(f'GLB access: {eyeriss.glb_access_per_layer["total"]} bytes')
        print(f'DRAM reads: {eyeriss.dram_access_per_layer["read"]} bytes')
        print(f'DRAM write: {eyeriss.dram_access_per_layer["write"]} bytes')
        print(f'DRAM access: {eyeriss.dram_access_per_layer["total"]} bytes')
        print(f'MACs: {eyeriss.macs_per_layer} ops')
        print(f'latency: {eyeriss.latency_per_layer} cycles')
        print(f'energy total: {eyeriss.energy_per_layer["total"]} uJ')
        print(f'power total: {eyeriss.power_per_layer["total"]} uW')
        print(f'operational intensity: {eyeriss.operational_intensity} ops/byte')
        print()

