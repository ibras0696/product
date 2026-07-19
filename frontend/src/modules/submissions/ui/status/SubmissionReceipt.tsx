import type { SubmissionStatusView } from "../../domain/submission";

export function SubmissionReceipt({
  receipt,
}: {
  receipt: SubmissionStatusView;
}) {
  return (
    <section className="submission-receipt" aria-labelledby="receipt-title">
      <span>Материал передан редакции</span>
      <h1 id="receipt-title">Спасибо за вклад в историю</h1>
      <p>
        Сохраните код. Из соображений безопасности он не записывается в адрес
        страницы или browser storage.
      </p>
      <div>
        <span>Код отслеживания</span>
        <strong>{receipt.trackingCode}</strong>
      </div>
      <a href="/">Вернуться к карте</a>
    </section>
  );
}
