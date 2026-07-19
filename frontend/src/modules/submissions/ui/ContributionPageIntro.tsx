interface ContributionPageIntroProps {
  online: boolean;
  needsRevision: boolean;
}

export function ContributionPageIntro(props: ContributionPageIntroProps) {
  return (
    <>
      <header className="submission-page-header">
        <a href="/">Паутина истории Чечни</a>
      </header>
      <section className="submission-intro">
        <span>Исторический атлас</span>
        <h1>Добавить материал</h1>
        <p>
          Предложите новую историю, уточнение, источник или фотографию. Заявка
          сохраняется как защищённый черновик перед загрузкой файлов.
        </p>
      </section>
      {!props.online ? (
        <div className="submission-offline" role="status">
          Соединение потеряно. Поля сохранены в памяти, отправка и загрузка
          отключены.
        </div>
      ) : null}
      {props.needsRevision ? (
        <div className="submission-revision" role="status">
          <strong>Нужны уточнения</strong>
          <p>
            Исправьте материал с учётом комментария редакции и отправьте снова.
          </p>
        </div>
      ) : null}
    </>
  );
}
