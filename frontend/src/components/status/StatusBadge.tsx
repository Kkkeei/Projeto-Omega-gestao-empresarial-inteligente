export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const cls =
    normalized.includes("NEGATIVA") || normalized.includes("REGULAR")
      ? "success"
      : normalized.includes("VENCIDA") || normalized.includes("IRREGULAR") || normalized.includes("POSITIVA")
      ? "danger"
      : normalized.includes("PENDENTE") || normalized.includes("PRÓXIMA")
      ? "warning"
      : "neutral";

  return <span className={`badge ${cls}`}>{value}</span>;
}