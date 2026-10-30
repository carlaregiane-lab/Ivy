export const MASS_UNITS = ["kg", "g"] as const;
export const ACCELERATION_UNITS = ["m/s2", "g0"] as const;
export const FORCE_UNITS = ["N", "kN"] as const;
export const LENGTH_UNITS = ["m", "cm", "mm"] as const;
export const AREA_UNITS = ["m2", "cm2", "mm2"] as const;
export const PRESSURE_UNITS = ["Pa", "kPa", "MPa", "bar"] as const;
export const TORQUE_UNITS = ["N.m", "N.mm"] as const;
export const TIME_UNITS = ["s", "min"] as const;
export const SPEED_UNITS = ["m/s", "mm/s"] as const;
export const POWER_UNITS = ["W", "kW"] as const;

type Quantity<Unit extends string> = { value: number; unit: Unit };
type MassUnit = (typeof MASS_UNITS)[number];
type AccelerationUnit = (typeof ACCELERATION_UNITS)[number];
type ForceUnit = (typeof FORCE_UNITS)[number];
type LengthUnit = (typeof LENGTH_UNITS)[number];
type AreaUnit = (typeof AREA_UNITS)[number];
type PressureUnit = (typeof PRESSURE_UNITS)[number];
type TorqueUnit = (typeof TORQUE_UNITS)[number];
type TimeUnit = (typeof TIME_UNITS)[number];
type SpeedUnit = (typeof SPEED_UNITS)[number];
type PowerUnit = (typeof POWER_UNITS)[number];

export type EngineeringCalculationInput =
  | {
      calculation: "forceFromMass";
      mass: Quantity<MassUnit>;
      acceleration: Quantity<AccelerationUnit>;
      outputUnit: ForceUnit;
    }
  | {
      calculation: "torqueFromForce";
      force: Quantity<ForceUnit>;
      leverArm: Quantity<LengthUnit>;
      outputUnit: TorqueUnit;
    }
  | {
      calculation: "pressureFromForce";
      force: Quantity<ForceUnit>;
      area: Quantity<AreaUnit>;
      outputUnit: PressureUnit;
    }
  | {
      calculation: "safetyFactor";
      capacity: number;
      demand: number;
    }
  | {
      calculation: "leadScrewLinearForce";
      torque: Quantity<TorqueUnit>;
      lead: Quantity<LengthUnit>;
      efficiency: number;
      outputUnit: ForceUnit;
    }
  | {
      calculation: "dcPower";
      voltage: number;
      current: number;
      outputUnit: PowerUnit;
    }
  | {
      calculation: "mechanicalPower";
      force: Quantity<ForceUnit>;
      speed: Quantity<SpeedUnit>;
      outputUnit: PowerUnit;
    }
  | {
      calculation: "linearSpeed";
      distance: Quantity<LengthUnit>;
      time: Quantity<TimeUnit>;
      outputUnit: SpeedUnit;
    };

export type EngineeringCalculationResult = {
  calculation: EngineeringCalculationInput["calculation"];
  label: string;
  formula: string;
  substitution: string;
  result: {
    value: number;
    unit: string;
    formatted: string;
  };
  warnings: string[];
};

const factors = {
  mass: { kg: 1, g: 0.001 },
  acceleration: { "m/s2": 1, g0: 9.80665 },
  force: { N: 1, kN: 1_000 },
  length: { m: 1, cm: 0.01, mm: 0.001 },
  area: { m2: 1, cm2: 0.0001, mm2: 0.000001 },
  pressure: { Pa: 1, kPa: 1_000, MPa: 1_000_000, bar: 100_000 },
  torque: { "N.m": 1, "N.mm": 0.001 },
  time: { s: 1, min: 60 },
  speed: { "m/s": 1, "mm/s": 0.001 },
  power: { W: 1, kW: 1_000 },
} as const;

const displayUnits: Record<string, string> = {
  "m/s2": "m/s²",
  g0: "g₀",
  m2: "m²",
  cm2: "cm²",
  mm2: "mm²",
  "N.m": "N·m",
  "N.mm": "N·mm",
};

function toBase(value: number, factor: number) {
  return value * factor;
}

function fromBase(value: number, factor: number) {
  return value / factor;
}

function rounded(value: number) {
  if (value === 0) return 0;
  const magnitude = Math.floor(Math.log10(Math.abs(value)));
  const scale = 10 ** (5 - magnitude);
  return Math.round(value * scale) / scale;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    maximumSignificantDigits: 6,
    useGrouping: false,
  }).format(value);
}

function shownUnit(unit: string) {
  return displayUnits[unit] ?? unit;
}

function quantity(value: number, unit: string) {
  return `${formatNumber(value)} ${shownUnit(unit)}`;
}

function result(
  input: EngineeringCalculationInput,
  label: string,
  formula: string,
  substitution: string,
  value: number,
  unit: string,
  warnings: string[] = []
): EngineeringCalculationResult {
  if (!Number.isFinite(value)) throw new Error("O cálculo produziu um resultado não finito.");
  const safeValue = rounded(value);
  return {
    calculation: input.calculation,
    label,
    formula,
    substitution,
    result: {
      value: safeValue,
      unit: shownUnit(unit),
      formatted: quantity(safeValue, unit),
    },
    warnings,
  };
}

export function calculateEngineering(input: EngineeringCalculationInput): EngineeringCalculationResult {
  switch (input.calculation) {
    case "forceFromMass": {
      const mass = toBase(input.mass.value, factors.mass[input.mass.unit]);
      const acceleration = toBase(input.acceleration.value, factors.acceleration[input.acceleration.unit]);
      const force = mass * acceleration;
      const value = fromBase(force, factors.force[input.outputUnit]);
      return result(
        input,
        "Força a partir da massa",
        "F = m · a",
        `F = ${quantity(mass, "kg")} × ${quantity(acceleration, "m/s2")}`,
        value,
        input.outputUnit
      );
    }
    case "torqueFromForce": {
      const force = toBase(input.force.value, factors.force[input.force.unit]);
      const leverArm = toBase(input.leverArm.value, factors.length[input.leverArm.unit]);
      const torque = force * leverArm;
      const value = fromBase(torque, factors.torque[input.outputUnit]);
      return result(
        input,
        "Torque a partir da força",
        "T = F · r",
        `T = ${quantity(force, "N")} × ${quantity(leverArm, "m")}`,
        value,
        input.outputUnit
      );
    }
    case "pressureFromForce": {
      const force = toBase(input.force.value, factors.force[input.force.unit]);
      const area = toBase(input.area.value, factors.area[input.area.unit]);
      const pressure = force / area;
      const value = fromBase(pressure, factors.pressure[input.outputUnit]);
      return result(
        input,
        "Pressão a partir da força",
        "p = F / A",
        `p = ${quantity(force, "N")} / ${quantity(area, "m2")}`,
        value,
        input.outputUnit
      );
    }
    case "safetyFactor": {
      const safetyFactor = input.capacity / input.demand;
      const warnings: string[] = [];
      if (safetyFactor < 1) warnings.push("A capacidade informada é menor que a demanda.");
      else if (safetyFactor < 1.5) warnings.push("A margem é estreita; defina o critério de aceitação aplicável ao projeto.");
      return result(
        input,
        "Fator de segurança",
        "n = capacidade / demanda",
        `n = ${formatNumber(input.capacity)} / ${formatNumber(input.demand)}`,
        safetyFactor,
        "adimensional",
        warnings
      );
    }
    case "leadScrewLinearForce": {
      const torque = toBase(input.torque.value, factors.torque[input.torque.unit]);
      const lead = toBase(input.lead.value, factors.length[input.lead.unit]);
      const force = (2 * Math.PI * torque * input.efficiency) / lead;
      const value = fromBase(force, factors.force[input.outputUnit]);
      const warnings = [
        "Resultado idealizado: não inclui atrito variável, flambagem, desalinhamento, inércia ou limites do conjunto.",
      ];
      return result(
        input,
        "Força linear idealizada do fuso",
        "F = 2π · T · η / avanço",
        `F = 2π × ${quantity(torque, "N.m")} × ${formatNumber(input.efficiency)} / ${quantity(lead, "m")}`,
        value,
        input.outputUnit,
        warnings
      );
    }
    case "dcPower": {
      const power = input.voltage * input.current;
      const value = fromBase(power, factors.power[input.outputUnit]);
      return result(
        input,
        "Potência elétrica em corrente contínua",
        "P = V · I",
        `P = ${quantity(input.voltage, "V")} × ${quantity(input.current, "A")}`,
        value,
        input.outputUnit,
        ["Potência de entrada; perdas e rendimento do sistema não estão incluídos."]
      );
    }
    case "mechanicalPower": {
      const force = toBase(input.force.value, factors.force[input.force.unit]);
      const speed = toBase(input.speed.value, factors.speed[input.speed.unit]);
      const power = force * speed;
      const value = fromBase(power, factors.power[input.outputUnit]);
      return result(
        input,
        "Potência mecânica linear",
        "P = F · v",
        `P = ${quantity(force, "N")} × ${quantity(speed, "m/s")}`,
        value,
        input.outputUnit
      );
    }
    case "linearSpeed": {
      const distance = toBase(input.distance.value, factors.length[input.distance.unit]);
      const time = toBase(input.time.value, factors.time[input.time.unit]);
      const speed = distance / time;
      const value = fromBase(speed, factors.speed[input.outputUnit]);
      return result(
        input,
        "Velocidade linear média",
        "v = d / t",
        `v = ${quantity(distance, "m")} / ${quantity(time, "s")}`,
        value,
        input.outputUnit
      );
    }
  }
}
