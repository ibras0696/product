import type { landingStyles } from "../model/landingStyles";
import { DeliveryPreview } from "./DeliveryPreview";

type LandingStyle = (typeof landingStyles)[number];

const mockCases = [
  ["Городской сервис", "Проверка обращений без очередей"],
  ["Образование", "Личный маршрут подготовки"],
  ["Команды", "Решения из встреч в задачи"],
  ["Маркетплейс", "Подбор исполнителя по контексту"],
] as const;

export function LandingContent({ selected }: { selected?: LandingStyle }) {
  return (
    <>
      <Hero />
      <Facts />
      <Principles />
      <Cases />
      <Footer selected={selected} />
    </>
  );
}

function Hero() {
  return (
    <section className="hero" id="top" aria-labelledby="page-title">
      <div className="hero-copy">
        <p className="hero-kicker">Product sprint platform</p>
        <h1 id="page-title">Из идеи в работающий продукт за один спринт.</h1>
        <p className="hero-lead">
          Проверяем ценность, собираем MVP и измеряем результат на одном стеке.
        </p>
        <div className="hero-actions">
          <a className="button primary" href="#cases">
            Смотреть демо
          </a>
          <a className="button secondary" href="/api/docs">
            Открыть API
          </a>
        </div>
      </div>
      <DeliveryPreview />
    </section>
  );
}

function Facts() {
  return (
    <section className="facts" aria-label="Свойства витрины">
      <div>
        <strong>10</strong>
        <span>систем дизайна</span>
      </div>
      <div>
        <strong>360 px</strong>
        <span>mobile-first</span>
      </div>
      <div>
        <strong>1 stack</strong>
        <span>React + FastAPI</span>
      </div>
    </section>
  );
}

function Principles() {
  return (
    <section
      className="principles"
      id="principles"
      aria-labelledby="principles-title"
    >
      <div className="section-intro">
        <h2 id="principles-title">Сначала решение. Потом код.</h2>
        <p>
          Один процесс связывает продуктовую гипотезу, требования, интерфейс и
          проверяемое поведение.
        </p>
      </div>
      <div className="principles-grid">
        <article className="principle product">
          <span>Product</span>
          <h3>Ценность до функциональности</h3>
          <p>Фиксируем аудиторию, проблему, метрику и честный объём MVP.</p>
        </article>
        <article className="principle design">
          <span>Design</span>
          <h3>Система вместо набора экранов</h3>
          <p>Токены, состояния и адаптивность работают как одно целое.</p>
        </article>
        <article className="principle delivery">
          <span>Delivery</span>
          <h3>Каждое решение можно проверить</h3>
          <p>Сценарные тесты подтверждают важное поведение всего потока.</p>
        </article>
      </div>
    </section>
  );
}

function Cases() {
  return (
    <section className="cases" id="cases" aria-labelledby="cases-title">
      <div className="section-intro">
        <h2 id="cases-title">Один подход для разных кейсов.</h2>
        <p>Примеры ниже являются мок-данными для проверки композиции.</p>
      </div>
      <div
        className="case-track"
        tabIndex={0}
        aria-label="Примеры кейсов, прокручиваемая область"
      >
        {mockCases.map(([category, title]) => (
          <article className="case" key={category}>
            <span>{category}</span>
            <h3>{title}</h3>
            <p>Проблема, узкий сценарий, измеримый результат.</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Footer({ selected }: { selected?: LandingStyle }) {
  return (
    <footer className="site-footer">
      <strong>Product Lab</strong>
      <p aria-live="polite">
        Выбран стиль: {selected?.name}. {selected?.note}.
      </p>
      <a href="mailto:hello@product.py-it.ru">hello@product.py-it.ru</a>
    </footer>
  );
}
