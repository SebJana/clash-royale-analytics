import { Component, type ReactNode } from "react";
import { PlayerError } from "./playerError";

export class PlayerErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <PlayerError
          sources={[
            {
              label: "this page",
              failed: true,
              retry: async () => this.setState({ hasError: false }),
            },
          ]}
          message="Something went wrong while displaying this page. Please try again."
        />
      );
    }

    return this.props.children;
  }
}
