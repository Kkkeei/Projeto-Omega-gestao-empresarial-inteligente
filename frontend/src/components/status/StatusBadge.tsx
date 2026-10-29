export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const cls =
    normalized.includes("VENCIDA") || normalized.includes("IRREGULAR") || normalized.includes("ERRO")
      ? "danger"
      : normalized.includes("POSITIVA COM EFEITOS") || normalized.includes("POSITIVA") ||
        normalized.includes("PENDENTE") || normalized.includes("PRÓXIMA")
      ? "warning"
      : normalized.includes("NEGATIVA") || normalized.includes("REGULAR")
      ? "success"
      : "neutral";

  return <span className={`badge ${cls}`}>{value}</span>;
}
