import type { ActuatorCadResult } from "./actuator-cad.ts";

type Point = [number, number, number];
type Triangle = [Point, Point, Point];

function normal([a, b, c]: Triangle): Point {
  const u: Point = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  const v: Point = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  const n: Point = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
  const length = Math.hypot(...n) || 1;
  return [n[0] / length, n[1] / length, n[2] / length];
}

function box(cx: number, cy: number, cz: number, width: number, depth: number, height: number): Triangle[] {
  const x = width / 2;
  const y = depth / 2;
  const z = height / 2;
  const p: Point[] = [
    [cx - x, cy - y, cz - z], [cx + x, cy - y, cz - z],
    [cx + x, cy + y, cz - z], [cx - x, cy + y, cz - z],
    [cx - x, cy - y, cz + z], [cx + x, cy - y, cz + z],
    [cx + x, cy + y, cz + z], [cx - x, cy + y, cz + z],
  ];
  const faces = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]];
  return faces.map(([a, b, c]) => [p[a], p[b], p[c]] as Triangle);
}

function cylinder(cx: number, cy: number, z0: number, radius: number, height: number, segments = 20): Triangle[] {
  const triangles: Triangle[] = [];
  for (let index = 0; index < segments; index += 1) {
    const a = (index / segments) * Math.PI * 2;
    const b = ((index + 1) / segments) * Math.PI * 2;
    const p1: Point = [cx + Math.cos(a) * radius, cy + Math.sin(a) * radius, z0];
    const p2: Point = [cx + Math.cos(b) * radius, cy + Math.sin(b) * radius, z0];
    const p3: Point = [p2[0], p2[1], z0 + height];
    const p4: Point = [p1[0], p1[1], z0 + height];
    triangles.push([p1, p2, p3], [p1, p3, p4], [[cx, cy, z0], p2, p1], [[cx, cy, z0 + height], p4, p3]);
  }
  return triangles;
}

function facet(triangle: Triangle) {
  const n = normal(triangle);
  const vertices = triangle.map((point) => `      vertex ${point.join(" ")}`).join("\n");
  return `  facet normal ${n.join(" ")}\n    outer loop\n${vertices}\n    endloop\n  endfacet`;
}

export function generateActuatorStl(model: ActuatorCadResult) {
  const { overallWidthMm: width, overallDepthMm: depth, overallHeightMm: height, travelMm, screwNominalDiameterMm, guideProfileSizeMm } = model.parameters;
  const carriageZ = 80 + travelMm * 0.5;
  const triangles: Triangle[] = [
    ...box(0, 0, 6, width, depth, 12),
    ...box(0, 0, height - 8, width * 0.86, depth * 0.82, 16),
    ...box(0, 0, carriageZ, width * 0.72, depth * 0.72, 18),
    ...box(0, -depth * 0.42, carriageZ + 14, width * 0.88, depth * 0.22, 10),
    ...box(0, 0, 35, width * 0.42, depth * 0.48, 46),
    ...cylinder(-width * 0.28, 0, 12, guideProfileSizeMm / 2, height - 32),
    ...cylinder(width * 0.28, 0, 12, guideProfileSizeMm / 2, height - 32),
    ...cylinder(0, 0, 12, screwNominalDiameterMm / 2, height - 32),
  ];
  return `solid ${model.modelId}\n${triangles.map(facet).join("\n")}\nendsolid ${model.modelId}\n`;
}
