import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  ClipboardCheck,
  MessageSquare
} from "lucide-react";

import { fetchTeacherOverview } from "../services/apiClient";

type TeacherDashboardProps = {
  onBack: () => void;
};

export function TeacherDashboard({ onBack }: TeacherDashboardProps) {
  const { data, error, isLoading } = useQuery({
    queryKey: ["teacher-overview"],
    queryFn: fetchTeacherOverview
  });

  const averageScore =
    data?.average_simulation_score === null ||
    data?.average_simulation_score === undefined
      ? "Sin datos"
      : `${Math.round(data.average_simulation_score * 100)}%`;

  return (
    <section className="teacher-shell">
      <div className="teacher-header">
        <div>
          <p className="eyebrow">Panel docente</p>
          <h2>Analíticas de aprendizaje</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onBack}>
          <ArrowLeft aria-hidden="true" size={18} />
          Volver al asistente
        </button>
      </div>

      {isLoading ? (
        <div className="teacher-state">Cargando métricas...</div>
      ) : error ? (
        <div className="teacher-state error">
          No se pudieron cargar las métricas docentes.
        </div>
      ) : data ? (
        <>
          <div className="metrics-grid">
            <MetricCard
              icon={<BarChart3 aria-hidden="true" size={20} />}
              label="Estudiantes activos"
              value={data.active_students}
            />
            <MetricCard
              icon={<MessageSquare aria-hidden="true" size={20} />}
              label="Conversaciones totales"
              value={data.total_conversations}
            />
            <MetricCard
              icon={<ClipboardCheck aria-hidden="true" size={20} />}
              label="Simulaciones completadas"
              value={data.completed_simulations}
            />
            <MetricCard
              icon={<BarChart3 aria-hidden="true" size={20} />}
              label="Promedio en simulación"
              value={averageScore}
            />
          </div>

          <div className="teacher-band">
            <div>
              <BookOpen aria-hidden="true" size={22} />
              <span>Explícame</span>
              <strong>{data.explain_questions}</strong>
              <small>preguntas registradas</small>
            </div>
            <div>
              <MessageSquare aria-hidden="true" size={22} />
              <span>Explícame</span>
              <strong>{data.explain_answers}</strong>
              <small>respuestas generadas</small>
            </div>
            <div>
              <ClipboardCheck aria-hidden="true" size={22} />
              <span>Ejemplifica</span>
              <strong>{data.example_cases_answered}</strong>
              <small>casos resueltos</small>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

type MetricCardProps = {
  icon: ReactNode;
  label: string;
  value: string | number;
};

function MetricCard({ icon, label, value }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span>{icon}</span>
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  );
}
