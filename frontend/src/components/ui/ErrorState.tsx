export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-card error">
      <strong>Não foi possível carregar os dados.</strong>
      <span>{message}</span>
      {onRetry && <button className="button secondary" onClick={onRetry}>Tentar novamente</button>}
    </div>
  );
}