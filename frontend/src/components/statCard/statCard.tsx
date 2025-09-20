import "./statCard.css";

export function StatCard({
  value,
  label,
}: Readonly<{ value: string | number; label: string }>) {
  return (
    <div className="stat-card">
      <div className="stat-card-number">{value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}
