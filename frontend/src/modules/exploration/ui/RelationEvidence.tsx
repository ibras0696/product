import { useRelationSources } from "../api/explorationQueries";

export function RelationEvidence({ relationId }: { relationId: string }) {
  const query = useRelationSources(relationId);
  if (query.isPending) return <p role="status">Загружаем источники связи…</p>;
  if (query.isError)
    return <p role="alert">Источники связи временно недоступны.</p>;
  if (!query.data.items.length)
    return <p>Для этой связи источники не опубликованы.</p>;
  return (
    <ul className="hx-relation-sources">
      {query.data.items.map((source) => (
        <li key={source.id}>
          {source.url ? (
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title}
            </a>
          ) : (
            <strong>{source.title}</strong>
          )}
          {source.archive_reference ? (
            <small>{source.archive_reference}</small>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
