import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  ClipboardCheck,
  MessageSquare,
  Users
} from "lucide-react";

import {
  fetchTeacherConcepts,
  fetchTeacherOverview,
  fetchTeacherStudentAnalytics,
  fetchTeacherStudents
} from "../services/apiClient";
import type {
  CategoryPerformance,
  ConceptMetric,
  StudentConceptMastery,
  TeacherStudentSummary,
  TimelinePoint
} from "../shared/apiTypes";

type TeacherDashboardProps = {
  onBack: () => void;
};

export function TeacherDashboard({ onBack }: TeacherDashboardProps) {
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["teacher-overview"],
    queryFn: fetchTeacherOverview
  });
  const studentsQuery = useQuery({
    queryKey: ["teacher-students"],
    queryFn: fetchTeacherStudents
  });
  const conceptsQuery = useQuery({
    queryKey: ["teacher-concepts"],
    queryFn: fetchTeacherConcepts
  });
  const studentAnalyticsQuery = useQuery({
    queryKey: ["teacher-student-analytics", selectedStudentId],
    queryFn: () => fetchTeacherStudentAnalytics(selectedStudentId ?? ""),
    enabled: selectedStudentId !== null
  });

  useEffect(() => {
    if (!selectedStudentId && studentsQuery.data && studentsQuery.data.length > 0) {
      setSelectedStudentId(studentsQuery.data[0].student_id);
    }
  }, [selectedStudentId, studentsQuery.data]);

  const selectedStudent = useMemo(
    () =>
      studentsQuery.data?.find((student) => student.student_id === selectedStudentId) ??
      null,
    [selectedStudentId, studentsQuery.data]
  );

  const isLoading =
    overviewQuery.isLoading || studentsQuery.isLoading || conceptsQuery.isLoading;
  const hasError =
    overviewQuery.error || studentsQuery.error || conceptsQuery.error;
  const overview = overviewQuery.data;
  const concepts = conceptsQuery.data;

  const averageScore =
    overview?.average_simulation_score === null ||
    overview?.average_simulation_score === undefined
      ? "Sin datos"
      : `${Math.round(overview.average_simulation_score * 100)}%`;

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
      ) : hasError ? (
        <div className="teacher-state error">
          No se pudieron cargar las métricas docentes.
        </div>
      ) : overview ? (
        <>
          <div className="metrics-grid">
            <MetricCard
              icon={<Users aria-hidden="true" size={20} />}
              label="Estudiantes activos"
              value={overview.active_students}
            />
            <MetricCard
              icon={<MessageSquare aria-hidden="true" size={20} />}
              label="Conversaciones totales"
              value={overview.total_conversations}
            />
            <MetricCard
              icon={<ClipboardCheck aria-hidden="true" size={20} />}
              label="Simulaciones completadas"
              value={overview.completed_simulations}
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
              <strong>{overview.explain_questions}</strong>
              <small>preguntas registradas</small>
            </div>
            <div>
              <MessageSquare aria-hidden="true" size={22} />
              <span>Explícame</span>
              <strong>{overview.explain_answers}</strong>
              <small>respuestas generadas</small>
            </div>
            <div>
              <ClipboardCheck aria-hidden="true" size={22} />
              <span>Ejemplifica</span>
              <strong>{overview.example_cases_answered}</strong>
              <small>casos resueltos</small>
            </div>
          </div>

          <div className="teacher-analytics-grid">
            <StudentList
              students={studentsQuery.data ?? []}
              selectedStudentId={selectedStudentId}
              onSelect={setSelectedStudentId}
            />
            <ConceptRankings
              mostConsulted={concepts?.most_consulted ?? []}
              mostErrors={concepts?.most_errors ?? []}
            />
          </div>

          <StudentDetail
            selectedStudent={selectedStudent}
            isLoading={studentAnalyticsQuery.isLoading}
            mastery={studentAnalyticsQuery.data?.mastery_by_concept ?? []}
            categories={studentAnalyticsQuery.data?.category_performance ?? []}
            confusions={studentAnalyticsQuery.data?.confusions ?? []}
            timeline={studentAnalyticsQuery.data?.timeline ?? []}
          />
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

type StudentListProps = {
  students: TeacherStudentSummary[];
  selectedStudentId: string | null;
  onSelect: (studentId: string) => void;
};

function StudentList({ students, selectedStudentId, onSelect }: StudentListProps) {
  return (
    <section className="teacher-panel">
      <div className="teacher-panel-header">
        <div>
          <h3>Estudiantes</h3>
          <small>{students.length} registrados</small>
        </div>
        {students.length > 0 ? (
          <label className="student-selector">
            <span>Seleccionar estudiante</span>
            <select
              value={selectedStudentId ?? ""}
              onChange={(event) => onSelect(event.target.value)}
            >
              {students.map((student) => (
                <option key={student.student_id} value={student.student_id}>
                  {shortStudentId(student.student_id)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      {students.length === 0 ? (
        <p className="teacher-empty">Aún no hay actividad estudiantil.</p>
      ) : (
        <div className="teacher-table-wrap">
          <table className="teacher-table">
            <thead>
              <tr>
                <th>Estudiante</th>
                <th>Conv.</th>
                <th>Sim.</th>
                <th>Prom.</th>
                <th>Casos</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr
                  className={
                    student.student_id === selectedStudentId ? "selected" : ""
                  }
                  key={student.student_id}
                >
                  <td>
                    <button
                      className="link-table-button"
                      type="button"
                      onClick={() => onSelect(student.student_id)}
                    >
                      {shortStudentId(student.student_id)}
                    </button>
                    <small>{formatDate(student.last_activity)}</small>
                  </td>
                  <td>{student.conversations}</td>
                  <td>{student.completed_simulations}</td>
                  <td>{formatPercent(student.average_simulation_score)}</td>
                  <td>{student.example_attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

type ConceptRankingsProps = {
  mostConsulted: ConceptMetric[];
  mostErrors: ConceptMetric[];
};

function ConceptRankings({ mostConsulted, mostErrors }: ConceptRankingsProps) {
  return (
    <section className="teacher-panel">
      <div className="teacher-panel-header">
        <h3>Conceptos</h3>
        <small>ranking de práctica</small>
      </div>
      <div className="teacher-rankings">
        <MetricList
          title="Más practicados"
          empty="Aún no hay conceptos practicados."
          metrics={mostConsulted}
          value={(metric) => `${metric.attempts} intentos`}
        />
        <MetricList
          title="Con más errores"
          empty="Aún no hay errores registrados."
          metrics={mostErrors}
          value={(metric) =>
            `${metric.errors} errores · dominio ${formatPercent(metric.average_mastery)}`
          }
        />
      </div>
    </section>
  );
}

type MetricListProps = {
  title: string;
  empty: string;
  metrics: ConceptMetric[];
  value: (metric: ConceptMetric) => string;
};

function MetricList({ title, empty, metrics, value }: MetricListProps) {
  return (
    <div className="teacher-ranking-list">
      <h4>{title}</h4>
      {metrics.length === 0 ? (
        <p className="teacher-empty">{empty}</p>
      ) : (
        metrics.slice(0, 5).map((metric) => (
          <div className="teacher-ranking-row" key={`${title}-${metric.concept}`}>
            <span>{humanizeConcept(metric.concept)}</span>
            <small>{value(metric)}</small>
          </div>
        ))
      )}
    </div>
  );
}

type StudentDetailProps = {
  selectedStudent: TeacherStudentSummary | null;
  isLoading: boolean;
  mastery: StudentConceptMastery[];
  categories: CategoryPerformance[];
  confusions: {
    expected_category: string;
    selected_category: string;
    count: number;
  }[];
  timeline: TimelinePoint[];
};

function StudentDetail({
  selectedStudent,
  isLoading,
  mastery,
  categories,
  confusions,
  timeline
}: StudentDetailProps) {
  if (!selectedStudent) {
    return (
      <section className="teacher-panel">
        <p className="teacher-empty">
          Selecciona un estudiante para ver sus analíticas.
        </p>
      </section>
    );
  }

  if (isLoading) {
    return <div className="teacher-state">Cargando detalle del estudiante...</div>;
  }

  return (
    <section className="teacher-panel student-detail-panel">
      <div className="teacher-panel-header">
        <div>
          <h3>{shortStudentId(selectedStudent.student_id)}</h3>
          <small>Detalle de aprendizaje</small>
        </div>
        <small>Última actividad: {formatDate(selectedStudent.last_activity)}</small>
      </div>

      <div className="student-analytics-grid">
        <MasteryPanel mastery={mastery} />
        <CategoryPanel categories={categories} />
        <ConfusionPanel confusions={confusions} />
        <TimelinePanel timeline={timeline} />
      </div>
    </section>
  );
}

function MasteryPanel({ mastery }: { mastery: StudentConceptMastery[] }) {
  return (
    <article className="teacher-subpanel">
      <h4>Dominio por concepto</h4>
      {mastery.length === 0 ? (
        <p className="teacher-empty">Sin práctica adaptativa registrada.</p>
      ) : (
        mastery.slice(0, 8).map((item) => (
          <div className="mastery-row" key={item.concept}>
            <div>
              <strong>{humanizeConcept(item.concept)}</strong>
              <small>
                {item.attempts} intentos ·{" "}
                {item.last_answer_correct === null
                  ? "sin último resultado"
                  : item.last_answer_correct
                    ? "último correcto"
                    : "último incorrecto"}
              </small>
            </div>
            <span>{formatPercent(item.mastery_score)}</span>
            <div className="mastery-bar">
              <i style={{ width: `${Math.round(item.mastery_score * 100)}%` }} />
            </div>
          </div>
        ))
      )}
    </article>
  );
}

function CategoryPanel({ categories }: { categories: CategoryPerformance[] }) {
  return (
    <article className="teacher-subpanel">
      <h4>Aciertos y errores por categoría</h4>
      {categories.length === 0 ? (
        <p className="teacher-empty">Sin simulaciones cerradas todavía.</p>
      ) : (
        <div className="compact-table">
          {categories.map((category) => (
            <div key={category.category}>
              <strong>{category.category}</strong>
              <span>{category.correct} aciertos</span>
              <span>{category.incorrect} errores</span>
              <small>{formatPercent(category.accuracy)}</small>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function ConfusionPanel({
  confusions
}: {
  confusions: {
    expected_category: string;
    selected_category: string;
    count: number;
  }[];
}) {
  return (
    <article className="teacher-subpanel">
      <h4>Confusiones frecuentes</h4>
      {confusions.length === 0 ? (
        <p className="teacher-empty">No hay confusiones registradas.</p>
      ) : (
        confusions.map((confusion) => (
          <div className="confusion-row" key={`${confusion.expected_category}-${confusion.selected_category}`}>
            <span>
              Esperado <strong>{confusion.expected_category}</strong>
            </span>
            <span>
              Marcó <strong>{confusion.selected_category}</strong>
            </span>
            <small>{confusion.count} veces</small>
          </div>
        ))
      )}
    </article>
  );
}

function TimelinePanel({ timeline }: { timeline: TimelinePoint[] }) {
  return (
    <article className="teacher-subpanel">
      <h4>Evolución temporal</h4>
      {timeline.length === 0 ? (
        <p className="teacher-empty">Aún no hay puntos temporales.</p>
      ) : (
        timeline.slice(-6).map((point) => (
          <div className="timeline-row" key={point.period}>
            <strong>{formatDate(point.period)}</strong>
            <span>{point.example_attempts} casos</span>
            <span>{point.completed_simulations} simulaciones</span>
            <small>{formatPercent(point.average_simulation_score)}</small>
          </div>
        ))
      )}
    </article>
  );
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Sin datos";
  }
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin datos";
  }
  return new Intl.DateTimeFormat("es-PE", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function humanizeConcept(value: string): string {
  return value.replaceAll("_", " ");
}

function shortStudentId(value: string): string {
  if (value.includes("@")) {
    return value;
  }
  return value.length > 18 ? `${value.slice(0, 8)}...${value.slice(-6)}` : value;
}
