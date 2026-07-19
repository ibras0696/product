import {
  kadyrovOrbit,
  nozhayOrbit,
  type MapEntity,
  type OrbitNode,
} from "../model/historyData";
import { GraphNodeIcon } from "./GraphNodeIcon";

function RelationList({ relations }: { relations: OrbitNode[] }) {
  return (
    <ul className="hx-overview-relations" aria-label="Главные связи">
      {relations.slice(0, 4).map((relation) => (
        <li key={relation.label} className={`hx-kind-${relation.kind}`}>
          <GraphNodeIcon kind={relation.kind} />
          <span>
            <strong>{relation.label}</strong>
            <small>{relation.caption}</small>
          </span>
        </li>
      ))}
    </ul>
  );
}

export function PlaceOverview({ entity }: { entity: MapEntity }) {
  return (
    <div className="hx-overview-grid">
      <article>
        <span className="hx-section-label">Кратко</span>
        <h3>{entity.subtitle}</h3>
        <p>{entity.summary}</p>
        <dl className="hx-overview-facts">
          <div>
            <dt>Связей</dt>
            <dd>{entity.stats.relations}</dd>
          </div>
          <div>
            <dt>Источников</dt>
            <dd>{entity.stats.sources}</dd>
          </div>
          <div>
            <dt>Событий</dt>
            <dd>{entity.stats.events}</dd>
          </div>
        </dl>
      </article>
      <article>
        <span className="hx-section-label">Главные связи</span>
        <RelationList relations={nozhayOrbit} />
      </article>
      <article className="hx-overview-source">
        <span className="hx-section-label">Последние источники</span>
        <strong>Архивные карточки Ножай-Юртовского района</strong>
        <p>
          Подборка документов, фотографий и свидетельств для проверки редакцией.
        </p>
      </article>
    </div>
  );
}

export function PersonOverview() {
  return (
    <div className="hx-person-overview">
      <article>
        <span className="hx-section-label">Биография</span>
        <h3>Ахмат-Хаджи Кадыров</h3>
        <p>
          Первый Президент Чеченской Республики, Герой России. Материалы
          объединяют места, события и архивные свидетельства.
        </p>
      </article>
      <ol className="hx-key-dates" aria-label="Ключевые даты">
        <li>
          <time>1951</time>
          <span>Начало жизненного пути</span>
        </li>
        <li>
          <time>2003</time>
          <span>Руководство республикой</span>
        </li>
        <li>
          <time>2004</time>
          <span>Историческая память</span>
        </li>
      </ol>
      <article>
        <span className="hx-section-label">Главные связи</span>
        <RelationList relations={kadyrovOrbit} />
      </article>
      <article className="hx-overview-source">
        <span className="hx-section-label">Последние источники</span>
        <strong>Документы и архивные карточки</strong>
        <p>
          12 опубликованных материалов доступны для последовательной проверки.
        </p>
      </article>
    </div>
  );
}
