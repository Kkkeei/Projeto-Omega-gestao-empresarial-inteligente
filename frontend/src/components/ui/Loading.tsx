export function Loading({ text = "Carregando..." }: { text?: string }) {
  return <div className="state-card"><div className="spinner" /><span>{text}</span></div>;
}