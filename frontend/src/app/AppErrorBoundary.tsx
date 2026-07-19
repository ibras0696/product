import { Component, type ReactNode } from "react";

import { StatePanel } from "@/shared/ui";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="app-state-page">
          <StatePanel
            tone="danger"
            title="Экран не загрузился"
            description="Обновите страницу. Если ошибка повторится, вернитесь к карте."
            action={<a href="/">Вернуться к карте</a>}
          />
        </main>
      );
    }
    return this.props.children;
  }
}
